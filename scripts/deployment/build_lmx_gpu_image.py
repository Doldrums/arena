#!/usr/bin/env python3
"""Build a private, wheel-locked LMX runtime; never run or admit a model.

Public package resolution is followed by offline installation and a UID 998
import check. Model weights and matching host driver libraries stay outside the
image. Run on the Linux worker; a new output directory and tag are mandatory.
"""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import http.client
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import time
from urllib.request import urlopen
import uuid
import zipfile


BASE = "127.0.0.1:5000/empira/canonical-small-cpu@sha256:5483308aca52e347ea81e4739d9789e76765d63a91ce2b62f41cb314af4446cc"
BASE_ID = "sha256:eb2be424496861e80bbed6b3f68e59424d143906f224d7fa64b9bbd08d90297a"
ASSET_SHA = "d0317d08be943f5105f7bd148c9bad6f5dba6e07bed85ed63007bdae3418c9c5"
MODEL_REVISION = "2880f2ca379f41b0226444936bb7a6766a227587"
PINS = {
    "torch": "2.9.1+cu128", "torchvision": "0.24.1+cu128", "diffusers": "0.35.2",
    "transformers": "4.57.3", "pillow": "11.3.0", "safetensors": "0.7.0",
    "ftfy": "6.3.1", "numpy": "2.2.6", "scipy": "1.15.3",
}
TORCH = {
    "torch": ("torch-2.9.1%2Bcu128-cp311-cp311-manylinux_2_28_x86_64.whl",
              "2a1da940f0757621d098c9755f7504d791a72a40920ec85a4fd98b20253fca4e"),
    "torchvision": ("torchvision-0.24.1%2Bcu128-cp311-cp311-manylinux_2_28_x86_64.whl",
                    "1b44f67cbd8f36e2a58bfaa3176d35b37df55604adf5929e89006e531f849faa"),
}
TAG = re.compile(r"127\.0\.0\.1:5000/empira/canonical-lmx-gpu:[a-zA-Z0-9_.-]+")
NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]*")
VERSION = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9.!+_-]*")
HEX = re.compile(r"[0-9a-f]{64}")
LIMITS = ["--cpus", "2", "--memory", "8g", "--memory-swap", "8g", "--pids-limit", "256"]
ENV = ["--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1",
       "--env", "MKL_NUM_THREADS=1", "--env", "HF_HUB_OFFLINE=1",
       "--env", "TRANSFORMERS_OFFLINE=1", "--env", "HF_HOME=/tmp/huggingface",
       "--env", "PYTHONDONTWRITEBYTECODE=1"]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    path.chmod(0o600)


def model_lock(path):
    if path.is_symlink() or not path.is_file() or digest(path) != ASSET_SHA:
        raise ValueError("Expected the reviewed model asset lock bytes")
    value = json.loads(path.read_bytes())
    if (value.get("schema") != "arena.lmx-sd-assets/1"
            or value.get("model_id") != "CompVis/stable-diffusion-v1-4"
            or value.get("revision") != MODEL_REVISION or value.get("gated") is not False
            or value.get("license") != "CreativeML OpenRAIL-M"):
        raise ValueError("Model identity or license differs from the reviewed contract")
    files = value.get("files", {})
    if len(files) != 17 or "LICENSE_SD.txt" not in files:
        raise ValueError("Model asset lock is incomplete")
    for name, record in files.items():
        item = PurePosixPath(name)
        if (item.is_absolute() or ".." in item.parts or item.as_posix() != name
                or "\\" in name or not HEX.fullmatch(record.get("sha256", ""))
                or type(record.get("size")) is not int or record["size"] <= 0):
            raise ValueError("Unsafe or unpinned model asset path")
    return value


def official_source(record):
    """Attest actual wheel bytes against the package publisher's distribution."""
    name = record["name"]
    if name in TORCH:
        filename, sha = TORCH[name]
        if (record["version"] != PINS[name] or record["sha256"] != sha
                or record["file"] != filename.replace("%2B", "+")):
            raise ValueError("PyTorch wheel differs from the pinned official artifact")
        return "https://download.pytorch.org/whl/cu128/" + filename
    with urlopen(f"https://pypi.org/pypi/{name}/{record['version']}/json", timeout=30) as response:
        evidence = json.load(response)
    matches = [row for row in evidence.get("urls", []) if row.get("filename") == record["file"]
               and row.get("digests", {}).get("sha256") == record["sha256"]
               and row.get("size") == record["size"] and row.get("packagetype") == "bdist_wheel"
               and row.get("url", "").startswith("https://files.pythonhosted.org/")]
    if len(matches) != 1:
        raise ValueError(f"Wheel lacks matching official PyPI provenance: {name}")
    return matches[0]["url"]


def wheel_lock(directory):
    records, names = [], set()
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".whl":
            raise ValueError("Expected only regular wheel files")
        with zipfile.ZipFile(path) as archive:
            entries = [p for p in archive.namelist() if p.count("/") == 1
                       and p.endswith(".dist-info/METADATA")]
            if len(entries) != 1:
                raise ValueError("Wheel metadata is missing or ambiguous")
            metadata = BytesParser().parsebytes(archive.read(entries[0]))
        name, version = metadata.get("Name", ""), metadata.get("Version", "")
        if not NAME.fullmatch(name) or not VERSION.fullmatch(version):
            raise ValueError("Invalid wheel distribution identity")
        name = normalize(name)
        if name in names or (name in PINS and PINS[name] != version):
            raise ValueError("Ambiguous wheel or changed required version")
        names.add(name)
        row = {"name": name, "version": version, "file": path.name,
               "sha256": digest(path), "size": path.stat().st_size}
        row["url"] = official_source(row)
        records.append(row)
    if not set(PINS) <= names:
        raise ValueError("Wheel set does not cover the complete runtime")
    records.sort(key=lambda row: row["name"])
    lock = "".join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in records)
    return lock, records


def run(command, log):
    with log.open("ab") as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}); inspect {log}")


def inspect(reference):
    return json.loads(subprocess.check_output(["docker", "image", "inspect", reference]))[0]


def check_image(value):
    config = value.get("Config", {})
    if (value.get("Os") != "linux" or value.get("Architecture") != "amd64"
            or config.get("Entrypoint") not in (None, []) or config.get("Cmd") != ["python3"]
            or config.get("OnBuild")):
        raise ValueError("Expected Linux amd64, no entrypoint/OnBuild and CMD python3")


def registry_tag(tag):
    """Only an explicit 404 proves a private release tag is unclaimed."""
    if not TAG.fullmatch(tag):
        raise ValueError("Expected a private LMX image tag")
    repository, name = tag.removeprefix("127.0.0.1:5000/").split(":")
    client = http.client.HTTPConnection("127.0.0.1", 5000, timeout=15)
    try:
        client.request("GET", f"/v2/{repository}/manifests/{name}", headers={"Accept":
            "application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json"})
        response = client.getresponse()
        if response.status == 404:
            return None
        if response.status != 200:
            raise ValueError("Private registry state could not be verified")
        raw = response.read(8 * 1024 * 1024 + 1)
        sha = response.getheader("Docker-Content-Digest")
        if len(raw) > 8 * 1024 * 1024 or sha != "sha256:" + hashlib.sha256(raw).hexdigest():
            raise ValueError("Registry manifest digest is inconsistent")
        value = json.loads(raw)
        image_id = value.get("config", {}).get("digest", "")
        if value.get("schemaVersion") != 2 or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            raise ValueError("Expected a single-platform registry manifest")
        return {"reference": "127.0.0.1:5000/" + repository + "@" + sha, "image_id": image_id}
    finally:
        client.close()


def import_script():
    return "\n".join([
        "import importlib.metadata, json, pathlib, subprocess, sys",
        "import torch, torchvision, diffusers, transformers, PIL, safetensors, ftfy, numpy, scipy",
        "from diffusers import StableDiffusionPipeline",
        "from diffusers.pipelines.stable_diffusion.safety_checker import StableDiffusionSafetyChecker",
        "from transformers import CLIPTokenizer, CLIPTextModel, CLIPImageProcessor",
        f"pins = {PINS!r}",
        "assert all(importlib.metadata.version(k) == v for k, v in pins.items())",
        "assert torch.version.cuda == '12.8'",
        "assert not list(pathlib.Path('/dev').glob('nvidia*'))",
        "subprocess.run([sys.executable, '-m', 'pip', 'check'], check=True)",
        "packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}",
        "print('ARENA_LMX_PROBE=' + json.dumps({'packages': packages, 'python': sys.version,",
        "  'torch_cuda': torch.version.cuda, 'model_loaded': False}, sort_keys=True))",
    ])


def install_script():
    return "\n".join([
        "import os, pathlib, shutil, subprocess, sys",
        "os.umask(0o022)",
        "subprocess.run([sys.executable, '-m', 'pip', '--isolated', 'install',",
        "  '--disable-pip-version-check', '--no-cache-dir', '--no-index', '--find-links=/wheels',",
        "  '--require-hashes', '-r', '/lock/requirements.lock'], check=True)",
        "root = pathlib.Path('/opt/arena-image'); root.mkdir(parents=True, exist_ok=True)",
        "root.chmod(0o755)",
        "for name in ('requirements.lock', 'wheels.json', 'model-assets.json'):",
        "    shutil.copyfile('/lock/' + name, root / name); (root / name).chmod(0o644)",
        import_script(),
    ])


def probe(path):
    prefix = "ARENA_LMX_PROBE="
    values = [json.loads(line[len(prefix):]) for line in path.read_text().splitlines()
              if line.startswith(prefix)]
    if len(values) != 1:
        raise ValueError("Missing or ambiguous runtime inventory")
    return values[0]


def push_verified(tag, image_id, log):
    if registry_tag(tag) is not None or inspect(tag).get("Id") != image_id:
        raise ValueError("Release tag exists or changed after validation")
    run(["docker", "push", tag], log)
    published, built = registry_tag(tag), inspect(image_id)
    if (published is None or published["image_id"] != image_id or built.get("Id") != image_id
            or published["reference"] not in built.get("RepoDigests", [])):
        raise ValueError("Published image differs from the verified image bytes")
    return published["reference"]


def build(tag, output, asset_lock):
    output, asset_lock = Path(output), Path(asset_lock)
    if (not TAG.fullmatch(tag) or not output.is_absolute() or output.resolve() != output
            or output.exists() or "," in str(output)):
        raise ValueError("Use a new absolute private directory and a private LMX tag")
    assets = model_lock(asset_lock)
    parent = inspect(BASE)
    check_image(parent)
    if parent.get("Id") != BASE_ID or BASE not in parent.get("RepoDigests", []):
        raise ValueError("Installed base differs from its reviewed immutable identity")
    existing = subprocess.check_output(["docker", "image", "ls", "--quiet", "--filter", f"reference={tag}"])
    if existing.strip() or registry_tag(tag) is not None:
        raise ValueError("Refusing to overwrite a local or published image tag")
    output.mkdir(mode=0o700, parents=True)
    wheels = output / "wheels"
    wheels.mkdir(mode=0o700)
    (output / "model-assets.json").write_bytes(asset_lock.read_bytes())
    requirements = [f"{name}=={version}" for name, version in PINS.items() if name not in TORCH]
    requirements += [f"https://download.pytorch.org/whl/cu128/{file}#sha256={sha}"
                     for file, sha in TORCH.values()]
    (output / "requirements.in").write_text("\n".join(requirements) + "\n")
    started = time.time()
    run(["docker", "run", "--rm", *LIMITS, *ENV,
         "--mount", f"type=bind,src={output},dst=/artifacts", BASE,
         "python", "-m", "pip", "--isolated", "download", "--disable-pip-version-check",
         "--no-cache-dir", "--index-url", "https://pypi.org/simple", "--only-binary=:all:",
         "--dest", "/artifacts/wheels", "-r", "/artifacts/requirements.in"], output / "download.log")
    lock, records = wheel_lock(wheels)
    (output / "requirements.lock").write_text(lock)
    write_json(output / "wheels.json", records)
    lock_sha = digest(output / "requirements.lock")
    container = "arena-lmx-build-" + uuid.uuid4().hex
    try:
        script = install_script()
        (output / "install-and-check.py").write_text(script + "\n")
        run(["docker", "run", "--name", container, *LIMITS, *ENV, "--network", "none",
             "--mount", f"type=bind,src={wheels},dst=/wheels,readonly",
             "--mount", f"type=bind,src={output},dst=/lock,readonly",
             BASE, "python", "-c", script], output / "install.log")
        installed = probe(output / "install.log")
        versions = {normalize(k): v for k, v in installed["packages"].items()}
        if any(versions.get(row["name"]) != row["version"] for row in records):
            raise ValueError("Installed inventory does not match the complete wheel lock")
        run(["docker", "commit", "--change", "ENTRYPOINT []", "--change", 'CMD ["python3"]',
             "--change", "LABEL io.arena.profile=lmx-sd14-gpu",
             "--change", f"LABEL io.arena.requirements.sha256={lock_sha}",
             "--change", f"LABEL io.arena.model-assets.sha256={ASSET_SHA}",
             "--change", f"LABEL io.arena.base={BASE}", container, tag], output / "image.log")
        built = inspect(tag)
        check_image(built)
        image_id = built["Id"]
        smoke = import_script() + "\nimport hashlib\n"
        smoke += f"assert hashlib.sha256(pathlib.Path('/opt/arena-image/model-assets.json').read_bytes()).hexdigest() == {ASSET_SHA!r}\n"
        smoke += f"assert hashlib.sha256(pathlib.Path('/opt/arena-image/requirements.lock').read_bytes()).hexdigest() == {lock_sha!r}\n"
        run(["docker", "run", "--rm", *LIMITS, *ENV, "--network", "none", "--read-only",
             "--user", "998:998", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
             "--tmpfs", "/tmp:rw,nosuid,nodev,size=268435456", image_id,
             "python", "-c", smoke], output / "uid998-offline-import.log")
        if probe(output / "uid998-offline-import.log") != installed:
            raise ValueError("UID 998 runtime inventory differs from the installed image")
        reference = push_verified(tag, image_id, output / "image.log")
        receipt = {"schema": "arena.lmx-gpu-image/1", "base": BASE, "base_image_id": BASE_ID,
                   "image": reference, "image_id": image_id, "tag": tag,
                   "requirements_sha256": lock_sha, "wheels": records, "runtime": installed,
                   "model": {"id": assets["model_id"], "revision": MODEL_REVISION,
                             "asset_lock_sha256": ASSET_SHA, "assets_external": True},
                   "driver_libraries_external": True, "pip_check": "passed",
                   "uid998_offline_import": "passed", "network_during_install": "none",
                   "model_calls": 0, "model_loaded": False, "gpu_probe_executed": False,
                   "research_executed": False, "admitted": False,
                   "build_resources": {"cpus": 2, "memory_bytes": 8 * 1024 ** 3, "pids": 256},
                   "builder_sha256": digest(Path(__file__)),
                   "started_at": started, "finished_at": time.time()}
        write_json(output / "receipt.json", receipt)
        return receipt
    finally:
        subprocess.run(["docker", "rm", "-f", container], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--asset-lock", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = build(args.tag, args.output, args.asset_lock)
    print(json.dumps({"image": receipt["image"], "image_id": receipt["image_id"],
                      "receipt": str(args.output / "receipt.json"), "model_calls": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
