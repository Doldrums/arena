#!/usr/bin/env python3
"""Build a wheel-locked CPU evaluator image without engines or credentials.

Run on the Linux worker. Wheel resolution may use public PyPI; installation and
package validation have no network. Both containers are limited to 2 CPU / 8GiB.
The private output directory retains the complete lock and build receipt.
"""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import uuid
import zipfile


PACKAGES = (
    "numpy", "scipy", "scikit-learn", "cvxpy", "sympy", "shapely",
    "beautifulsoup4", "lxml", "matplotlib", "pykalman", "PyWavelets",
    "gymnasium", "networkx", "pandas",
)
IMPORTS = (
    "numpy", "scipy", "sklearn", "cvxpy", "sympy", "shapely", "bs4", "lxml",
    "matplotlib", "pykalman", "pywt", "gymnasium", "networkx", "pandas",
)
IMAGE = re.compile(r"127\.0\.0\.1:5000/empira/[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}")
TAG = re.compile(r"127\.0\.0\.1:5000/empira/[a-z0-9][a-z0-9._/-]*:[a-zA-Z0-9_.-]+")
PACKAGE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._-]*")
VERSION = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9.!+_-]*")
LIMITS = ["--cpus", "2", "--memory", "8g", "--memory-swap", "8g", "--pids-limit", "256"]
THREAD_ENV = ["--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1",
              "--env", "MKL_NUM_THREADS=1", "--env", "NUMEXPR_NUM_THREADS=1"]


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    path.chmod(0o600)


def wheel_lock(directory, required=PACKAGES):
    """Lock each downloaded wheel using its embedded identity and actual bytes."""
    records, identities = [], set()
    for path in sorted(directory.iterdir()):
        if path.is_symlink() or not path.is_file() or path.suffix != ".whl":
            raise ValueError("Wheel directory must contain only regular wheel files")
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist()
                     if name.count("/") == 1 and name.endswith(".dist-info/METADATA")]
            if len(names) != 1:
                raise ValueError("Wheel requires exactly one package metadata file")
            metadata = BytesParser().parsebytes(archive.read(names[0]))
        name, version = metadata.get("Name", ""), metadata.get("Version", "")
        if not PACKAGE.fullmatch(name) or not VERSION.fullmatch(version):
            raise ValueError("Invalid wheel distribution identity")
        name = normalize(name)
        if name in identities:
            raise ValueError("Multiple wheels for the same distribution are ambiguous")
        identities.add(name)
        records.append({"name": name, "version": version, "file": path.name,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    if not {normalize(name) for name in required} <= identities:
        raise ValueError("Downloaded wheels do not cover every requested distribution")
    records.sort(key=lambda row: row["name"])
    lock = "".join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in records)
    return lock, records


def run(command, log):
    with log.open("ab") as handle:
        result = subprocess.run(command, stdout=handle, stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f"Command failed with exit code {result.returncode}; inspect {log}")


def inspect(reference):
    return json.loads(subprocess.check_output(["docker", "image", "inspect", reference]))[0]


def verify_image_command(inspection):
    config = inspection.get("Config", {})
    if config.get("Entrypoint") not in (None, []) or config.get("Cmd") != ["python3"]:
        raise ValueError("Evaluator image must have no entrypoint and CMD python3")


def validation_script():
    return "\n".join([
        "import importlib, importlib.metadata, json, subprocess, sys",
        "subprocess.run([sys.executable, '-m', 'pip', '--isolated', 'install',",
        "  '--disable-pip-version-check', '--no-index', '--find-links=/wheels',",
        "  '--require-hashes', '-r', '/lock/requirements.lock'], check=True)",
        "subprocess.run([sys.executable, '-m', 'pip', 'check'], check=True)",
        f"for name in {IMPORTS!r}: importlib.import_module(name)",
        "import cvxpy, gymnasium",
        "assert 'CLARABEL' in cvxpy.installed_solvers()",
        "for name in ('CartPole-v1', 'Acrobot-v1', 'MountainCar-v0'):",
        "    env = gymnasium.make(name)",
        "    env.reset(seed=0)",
        "    env.step(env.action_space.sample())",
        "    env.close()",
        "packages = {d.metadata['Name']: d.version for d in importlib.metadata.distributions()}",
        "print('ARENA_PACKAGE_PROBE=' + json.dumps({'packages': packages,",
        "  'solvers': cvxpy.installed_solvers(), 'python': sys.version}, sort_keys=True))",
    ])


def build(base, tag, output):
    output = Path(output)
    if not IMAGE.fullmatch(base) or not TAG.fullmatch(tag):
        raise ValueError("Use a digest-pinned private base and a private local-registry output tag")
    if not output.is_absolute() or output.resolve() != output or output.exists():
        raise ValueError("Output must be a new absolute directory without symlinks")
    base_info = inspect(base)
    if base not in base_info.get("RepoDigests", []):
        raise ValueError("Installed base image does not attest the supplied registry digest")
    verify_image_command(base_info)
    output.mkdir(mode=0o700, parents=True)
    wheels = output / "wheels"
    wheels.mkdir(mode=0o700)
    (output / "requirements.in").write_text("\n".join(PACKAGES) + "\n")
    resolve_script = "\n".join([
        "import importlib.metadata, json, pathlib, subprocess, sys",
        "root = pathlib.Path('/artifacts')",
        "pins = {name: importlib.metadata.version(name) for name in ('numpy', 'scipy')}",
        "(root / 'base-constraints.txt').write_text(''.join(f'{k}=={v}\\n' for k,v in pins.items()))",
        "subprocess.run([sys.executable, '-m', 'pip', '--isolated', 'download',",
        "  '--disable-pip-version-check', '--index-url', 'https://pypi.org/simple',",
        "  '--only-binary=:all:', '--dest', '/artifacts/wheels',",
        "  '--constraint', '/artifacts/base-constraints.txt', '-r', '/artifacts/requirements.in'], check=True)",
    ])
    started = time.time()
    run(["docker", "run", "--rm", *LIMITS, *THREAD_ENV,
         "--mount", f"type=bind,src={output},dst=/artifacts", "--entrypoint", "python",
         base, "-c", resolve_script], output / "download.log")
    lock, records = wheel_lock(wheels)
    (output / "requirements.lock").write_text(lock)
    lock_hash = hashlib.sha256(lock.encode()).hexdigest()
    write_json(output / "wheels.json", records)
    container = "arena-cpu-build-" + uuid.uuid4().hex
    script = validation_script()
    (output / "install-and-check.py").write_text(script + "\n")
    try:
        run(["docker", "run", "--name", container, *LIMITS, *THREAD_ENV,
             "--network", "none", "--mount", f"type=bind,src={wheels},dst=/wheels,readonly",
             "--mount", f"type=bind,src={output},dst=/lock,readonly",
             base, "python", "-c", script], output / "install.log")
        prefix = "ARENA_PACKAGE_PROBE="
        lines = (output / "install.log").read_text().splitlines()
        probes = [json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
        if len(probes) != 1:
            raise ValueError("Missing or ambiguous installed-package validation evidence")
        installed = {normalize(k): v for k, v in probes[0]["packages"].items()}
        if any(installed.get(row["name"]) != row["version"] for row in records):
            raise ValueError("Installed distributions do not match the hash-locked wheels")
        run(["docker", "commit", "--change", 'ENTRYPOINT []', "--change", 'CMD ["python3"]',
             "--change", "LABEL io.arena.profile=catalog-small-cpu",
             "--change", f"LABEL io.arena.requirements.sha256={lock_hash}",
             "--change", f"LABEL io.arena.base={base}", container, tag], output / "image.log")
        verify_image_command(inspect(tag))
        smoke = f"import importlib; [importlib.import_module(name) for name in {IMPORTS!r}]"
        run(["docker", "run", "--rm", *LIMITS, "--network", "none", "--read-only",
             "--user", "1000:1000", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
             "--tmpfs", "/tmp:rw,nosuid,nodev,size=268435456", "--env", "PYTHONDONTWRITEBYTECODE=1",
             tag, "python", "-c", smoke], output / "canonical-command.log")
        run(["docker", "push", tag], output / "image.log")
        built = inspect(tag)
        repository = tag.rsplit(":", 1)[0]
        refs = [ref for ref in built.get("RepoDigests", []) if ref.startswith(repository + "@sha256:")]
        if len(refs) != 1:
            raise ValueError("Pushed image has no unique immutable repository digest")
        receipt = {"schema": "arena.catalog-cpu-image/1", "base": base,
                   "base_image_id": base_info["Id"], "image": refs[0], "image_id": built["Id"],
                   "tag": tag, "requirements_sha256": lock_hash, "wheels": records,
                   "validation": probes[0], "pip_check": "passed", "canonical_command_probe": "passed",
                   "network_during_install": "none",
                   "build_resources": {"cpus": 2, "memory_bytes": 8 * 1024 ** 3, "pids": 256},
                   "model_calls": 0, "research_executed": False,
                   "started_at": started, "finished_at": time.time()}
        write_json(output / "receipt.json", receipt)
        return receipt
    finally:
        subprocess.run(["docker", "rm", "-f", container], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = build(args.base, args.tag, args.output)
    print(json.dumps({"image": receipt["image"], "image_id": receipt["image_id"],
                      "receipt": str(args.output / "receipt.json"), "pip_check": receipt["pip_check"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
