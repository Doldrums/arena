#!/usr/bin/env python3
"""Generate reviewed native DGM image contexts; never builds or runs an image."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from arena.frameworks.drivers.dgm_gateway import DGM_COMMIT, provider_overlays
from prepare_dgm_pilots import AIDER_COMMIT, SWEBENCH_COMMIT, TASKS, verify_git, files

BOOTSTRAP = """#!/bin/sh
set -eu
test ! -e /tmp/.arena-dgm-ready
for pair in 'arena-dgm-template dgm' 'arena-testbed-template testbed' 'arena-home-template root'; do
    set -- $pair
    source=/opt/$1
    destination=/$2
    test -d "$source" && test ! -L "$source"
    test -d "$destination" && test ! -L "$destination"
    test -z "$(find "$destination" -mindepth 1 -maxdepth 1 -print -quit)"
    cp -a --no-preserve=ownership "$source"/. "$destination"/
done
touch /tmp/.arena-dgm-ready
exec tail -f /dev/null
"""

COMMON = """
COPY integration/ /opt/arena-provider/
COPY arena-dgm-bootstrap /usr/local/bin/arena-dgm-bootstrap
RUN chmod 0555 /usr/local/bin/arena-dgm-bootstrap && mkdir -p /opt/arena-build-evidence
ENV PYTHONPATH=/opt/arena-provider PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1
LABEL io.arena.dgm.contract="dgm-prebuilt-v1" org.opencontainers.image.revision="a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2"
"""

# Native WORKDIR is one of the moved trees; leave it before overlayfs rename.
FINAL = """
RUN cd / && mkdir -p /dgm /testbed /opt/arena-home-template /opt/arena-native-home \\
 && for file in .bashrc .profile .condarc .gitconfig; do if [ -f /root/$file ] && [ ! -L /root/$file ]; then cp -a /root/$file /opt/arena-home-template/$file; fi; done \\
 && for dir in .cargo .rustup; do if [ -d /root/$dir ]; then mv /root/$dir /opt/arena-native-home/$dir; ln -s /opt/arena-native-home/$dir /opt/arena-home-template/$dir; fi; done \\
 && mv /dgm /opt/arena-dgm-template && mv /testbed /opt/arena-testbed-template \\
 && mkdir /dgm /testbed \\
 && python -m pip freeze > /opt/arena-build-evidence/runtime-pip-freeze.txt \\
 && python --version > /opt/arena-build-evidence/runtime-python.txt \\
 && python -m pip check > /opt/arena-build-evidence/runtime-pip-check.txt \\
 && dpkg-query -W > /opt/arena-build-evidence/dpkg-packages.txt
ENV PIP_NO_INDEX=1
ENTRYPOINT ["/usr/local/bin/arena-dgm-bootstrap"]
CMD ["tail", "-f", "/dev/null"]
"""


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(data if isinstance(data, str) else json.dumps(data, indent=2) + "\n")


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def resolve_base(repository, tag):
    if (repository, tag) not in {("python", "3.10-slim"), ("buildpack-deps", "jammy")}:
        raise ValueError("Only the two reviewed Docker Hub base tags may be resolved")
    token_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/{repository}:pull"
    with urlopen(token_url, timeout=30) as response:
        token = json.load(response)["token"]
    def manifest(reference):
        request = Request(f"https://registry-1.docker.io/v2/library/{repository}/manifests/{reference}",
            headers={"Authorization": "Bearer " + token, "Accept": ", ".join((
                "application/vnd.oci.image.index.v1+json", "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.oci.image.manifest.v1+json", "application/vnd.docker.distribution.manifest.v2+json"))})
        with urlopen(request, timeout=30) as response:
            raw = response.read(8 * 1024 * 1024)
            actual = digest(raw)
            if response.headers.get("Docker-Content-Digest") != actual:
                raise ValueError("Registry manifest digest mismatch")
        return json.loads(raw), actual
    index, index_digest = manifest(tag)
    candidates = [item for item in index.get("manifests", []) if item.get("platform", {}).get("os") == "linux"
                  and item.get("platform", {}).get("architecture") == "amd64"]
    if len(candidates) != 1:
        raise ValueError("Expected exactly one native linux/amd64 base manifest")
    image, image_digest = manifest(candidates[0]["digest"])
    if image_digest != candidates[0]["digest"]:
        raise ValueError("Registry index did not bind the returned image")
    return {"tag": f"docker.io/library/{repository}:{tag}", "index_digest": index_digest,
            "manifest_digest": image_digest, "config_digest": image["config"]["digest"],
            "reference": f"docker.io/library/{repository}@{image_digest}", "platform": "linux/amd64"}


def copy_git(source, destination, commit, public_origin):
    verify_git(source, commit)
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "clone", "--no-local", "--no-hardlinks",
                    str(source), str(destination)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(destination), "remote", "set-url", "origin", public_origin], check=True)
    verify_git(destination, commit)
    # No hooks from the source checkout, credential helpers or URL credentials.
    shutil.rmtree(destination / ".git/hooks", ignore_errors=True)
    config = (destination / ".git/config").read_text()
    if re.search(r"credential|extraheader|https?://[^/\s]+@", config, re.I):
        raise ValueError("Credential-bearing Git configuration is forbidden")


def extras(directory):
    write(directory / "arena-dgm-bootstrap", BOOTSTRAP)
    helper = REPO / "src/arena/frameworks/drivers/dgm_gateway.py"
    write(directory / "integration/arena/frameworks/drivers/dgm_gateway.py", helper.read_text())
    for package in ("arena", "arena/frameworks", "arena/frameworks/drivers"):
        write(directory / "integration" / package / "__init__.py", "")
    write(directory / ".dockerignore", "context-manifest.json\n")


def preparation(root, prepared, destination, bases):
    source, swe = root / "sources/dgm", root / "dependencies/swe-bench-dgm"
    verify_git(source, DGM_COMMIT)
    verify_git(swe, SWEBENCH_COMMIT)
    manifest = json.loads((prepared / "preparation.json").read_text())
    if manifest["source_commit"] != DGM_COMMIT or manifest["benchmark"]["commit"] != AIDER_COMMIT:
        raise ValueError("Image inputs do not match the reviewed preparation pins")
    if files(prepared / "native-inputs") != manifest["native_input_files"]:
        raise ValueError("Prepared native task files changed")
    overlays = provider_overlays(source)
    if {name: hashlib.sha256(text.encode()).hexdigest() for name, text in overlays.items()} != manifest["provider_overlay_files"]:
        raise ValueError("Provider overlays differ from the preparation receipt")
    recipe_path = prepared / "native-image-recipes.json"
    if hashlib.sha256(recipe_path.read_bytes()).hexdigest() != manifest["native_image_recipes_sha256"]:
        raise ValueError("Native image recipe hash mismatch")
    recipes = json.loads(recipe_path.read_text())
    if set(recipes) != set(TASKS):
        raise ValueError("Only the two reviewed Python exercises may enter these images")
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    write(destination / "base-images.json", bases)
    jobs = []
    dgm = destination / "dgm"
    dgm.mkdir()
    copy_git(source, dgm / "source", DGM_COMMIT, "https://github.com/jennyzzt/dgm.git")
    for name, content in overlays.items():
        (dgm / "source" / name).write_text(content)
    copy_git(swe, dgm / "swebench", SWEBENCH_COMMIT, "https://github.com/SWE-bench/SWE-bench.git")
    extras(dgm)
    native_dockerfile = (source / "Dockerfile").read_text()
    native_dockerfile = native_dockerfile.replace("FROM python:3.10-slim", "FROM " + bases["python"]["reference"], 1)
    native_dockerfile = native_dockerfile.replace("COPY . .", "COPY source/ .", 1)
    native_dockerfile = native_dockerfile.replace("RUN pip install --no-cache-dir -r requirements.txt",
        "RUN mkdir -p /opt/arena-build-evidence\nRUN pip install --no-cache-dir --report /opt/arena-build-evidence/dgm-pip-install.json -r requirements.txt", 1)
    write(dgm / "Dockerfile", native_dockerfile + COMMON + "\nCOPY swebench/ /opt/pinned-swebench/\n"
        "RUN python -m pip install --no-cache-dir --report /opt/arena-build-evidence/swebench-pip-install.json /opt/pinned-swebench\n" + FINAL)
    jobs.append({"id": "dgm", "lookup": "dgm:latest", "registry_tag": "127.0.0.1:5000/arena-dgm:dgm-a565fd2", "runnable": True})
    first = recipes[TASKS[0]]
    base = destination / "polyglot-base"
    base.mkdir()
    text = first["base_dockerfile"].replace("FROM buildpack-deps:jammy", "FROM " + bases["buildpack-deps"]["reference"], 1)
    # Capture hashes of downloaded setup artifacts before native cleanup.
    text = text.replace("RUN ARCH=$(uname -m)", "RUN mkdir -p /opt/arena-build-evidence\nRUN ARCH=$(uname -m)", 1)
    text = text.replace("tar -C /usr/local -xzf go.tar.gz", "sha256sum go.tar.gz >> /opt/arena-build-evidence/downloads.sha256 && tar -C /usr/local -xzf go.tar.gz", 1)
    text = text.replace("RUN chmod +x /tmp/rustup.sh", "RUN sha256sum /tmp/rustup.sh >> /opt/arena-build-evidence/downloads.sha256 && chmod +x /tmp/rustup.sh", 1)
    text = text.replace("&& bash miniconda.sh", "&& sha256sum miniconda.sh >> /opt/arena-build-evidence/downloads.sha256 && bash miniconda.sh", 1)
    write(base / "Dockerfile", text)
    jobs.append({"id": "polyglot-base", "lookup": first["base_image"], "registry_tag": "127.0.0.1:5000/arena-dgm:polyglot-base-a565fd2", "runnable": False})
    env = destination / "polyglot-env"
    env.mkdir()
    copy_git(swe, env / "swebench", SWEBENCH_COMMIT, "https://github.com/SWE-bench/SWE-bench.git")
    write(env / "requirements.txt", (source / "requirements.txt").read_text())
    setup = first["setup_env_script"].replace("python -m pip install ", "python -m pip install --report /opt/arena-build-evidence/testbed-pip-install.json ", 1)
    write(env / "setup_env.sh", setup)
    extras(env)
    write(env / "Dockerfile", first["env_dockerfile"] + COMMON + "\nCOPY requirements.txt /opt/dgm-requirements.txt\nCOPY swebench/ /opt/pinned-swebench/\n"
        "RUN /opt/miniconda3/bin/python -m pip install --no-cache-dir --report /opt/arena-build-evidence/runtime-pip-install.json -r /opt/dgm-requirements.txt /opt/pinned-swebench\n"
        "RUN /opt/miniconda3/envs/testbed/bin/python -m pip freeze > /opt/arena-build-evidence/testbed-pip-freeze.txt \\\n && /opt/miniconda3/bin/conda list --explicit -n testbed > /opt/arena-build-evidence/testbed-conda-explicit.txt\n")
    jobs.append({"id": "polyglot-env", "lookup": first["env_image"], "registry_tag": "127.0.0.1:5000/arena-dgm:polyglot-env-a565fd2", "runnable": False})
    for task in TASKS:
        item = recipes[task]
        instance = destination / task
        instance.mkdir()
        write(instance / "setup_repo.sh", item["install_repo_script"])
        relative = Path("polyglot-benchmark/python/exercises/practice") / task.split("__", 1)[1]
        shutil.copytree(prepared / "native-inputs/polyglot" / relative, instance / "polyglot" / relative)
        write(instance / "Dockerfile", item["instance_dockerfile"] + FINAL)
        jobs.append({"id": task, "lookup": item["instance_image"], "registry_tag": "127.0.0.1:5000/arena-dgm:" + task.replace("__", "-") + "-a565fd2", "runnable": True})
    for job in jobs:
        directory = destination / job["id"]
        dockerfile = directory / "Dockerfile"
        lines = dockerfile.read_text().splitlines(keepends=True)
        first_from = next(i for i, line in enumerate(lines) if line.startswith("FROM "))
        lines.insert(first_from + 1, "RUN test \"$(cat /sys/fs/cgroup/cpu.max)\" = \"800000 100000\" \\\n && test \"$(cat /sys/fs/cgroup/memory.max)\" = \"25769803776\" \\\n && mkdir -p /opt/arena-build-evidence \\\n && cat /sys/fs/cgroup/cpu.max > /opt/arena-build-evidence/build-cpu.max \\\n && cat /sys/fs/cgroup/memory.max > /opt/arena-build-evidence/build-memory.max\n")
        dockerfile.write_text("".join(lines))
        # Contexts have no credentials, private runtime configs or host env files.
        suspicious = []
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise ValueError("Unexpected build-context symlink")
            if not path.is_file():
                continue
            if path.name == ".env" or path.suffix.lower() in {".pem", ".key", ".p12"}:
                suspicious.append(str(path.relative_to(directory)))
            if ".git/objects/" not in str(path) and path.stat().st_size <= 8 * 1024 * 1024:
                data = path.read_bytes()
                if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{24,}|\bgh[pousr]_[A-Za-z0-9_]{24,}|\beyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]+\.", data):
                    suspicious.append(str(path.relative_to(directory)))
        if suspicious:
            raise ValueError("Context secret scan requires review: " + ", ".join(suspicious))
        job["files"] = files(directory)
        job["context_sha256"] = hashlib.sha256(json.dumps(job["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        write(directory / "context-manifest.json", job)
    plan = {"schema": "arena.dgm-image-build-plan/1", "source_commit": DGM_COMMIT, "benchmark_commit": AIDER_COMMIT,
        "swebench_commit": SWEBENCH_COMMIT, "preparation_sha256": hashlib.sha256((prepared / "preparation.json").read_bytes()).hexdigest(),
        "platform": "linux/amd64", "bases": bases, "jobs": jobs, "secret_scan": "passed",
        "dependency_policy": "Native ranges resolved during authorized build; actual interpreter freezes and pip download reports recorded, not claimed as a preexisting lock",
        "model_calls": 0, "container_runs": 0, "image_builds": 0}
    write(destination / "build-plan.json", plan)
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--prepared", type=Path, default=Path("/srv/arena/configs/dgm-pilot-20260921"))
    parser.add_argument("--destination", type=Path, default=Path("/srv/arena/build/dgm-images-20260921"))
    options = parser.parse_args()
    if not all(path.is_absolute() for path in (options.root, options.prepared, options.destination)):
        parser.error("All preparation paths must be absolute")
    bases = {"python": resolve_base("python", "3.10-slim"), "buildpack-deps": resolve_base("buildpack-deps", "jammy")}
    plan = preparation(options.root, options.prepared, options.destination, bases)
    print(json.dumps({"destination": str(options.destination), "contexts": len(plan["jobs"]), "secret_scan": plan["secret_scan"], "bases": bases}, indent=2))
