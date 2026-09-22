#!/usr/bin/env python3
"""Prepare a reviewed offline science5 image recipe; never build or run Docker.

Inputs are the exact private data, wheel and base-image receipts. The output
copies only two official wheels and nine runtime files, without source archives,
preparation-only dependencies, credentials, candidates or evaluator execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.sciel_catalog_science5 import (
    DATA_LOCK_SHA256, GROUP, PRESERVED_RUNTIME, PROFILE, RESOURCE_PROFILE, RUNTIME_ADDITIONS, TASKS,
)

BASE = ("127.0.0.1:5000/empira/canonical-small-cpu@sha256:"
        "5483308aca52e347ea81e4739d9789e76765d63a91ce2b62f41cb314af4446cc")
BASE_ID = "sha256:eb2be424496861e80bbed6b3f68e59424d143906f224d7fa64b9bbd08d90297a"
BASE_RECEIPT_SHA256 = "82f77ec3539410a19be237b044148c96cc7235109f44858b9725375ecf305590"
WHEEL_LOCK_SHA256 = "7b2ddfbcfc8d9b790cca3e47a28e9234cdd3abf10c7848ceee888a69f097256e"
WHEEL_PINS = {
    "viennarna": "5ae022916f1de3c6c80c9e806556a9942a7a57b029161b4bdbdbc1df06da80f5",
    "rdkit": "dcf09347e1a0dc1d7e5fcc34f5da79d1f4bb0e04ecadee669449b82ae2492799",
}
DATA_ROOT = "/opt/arena-science5-data"
SUPPORT_ROOT = "/opt/arena-science5-support"


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def checked_path(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("Inputs require absolute paths without symlinks or traversal")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("Symlinked inputs are not allowed")
    return path


def read(path, digest, size=None, maximum=64 * 1024 ** 2):
    path = checked_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
            raise ValueError("Input must be a bounded regular file")
        raw = handle.read(maximum + 1)
    if len(raw) > maximum or size is not None and len(raw) != size:
        raise ValueError("Input size differs from its immutable lock")
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Input bytes differ from the reviewed SHA256")
    return raw


def relative(value):
    if type(value) is not str or "\\" in value or "\x00" in value:
        raise ValueError("Invalid locked relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value or not path.parts:
        raise ValueError("Invalid locked relative path")
    return value


def inputs(data_lock, cache_root, base_receipt, wheel_lock, wheels):
    data_raw = read(data_lock, DATA_LOCK_SHA256, maximum=1024 ** 2)
    wheel_raw = read(wheel_lock, WHEEL_LOCK_SHA256, maximum=2 * 1024 ** 2)
    base_raw = read(base_receipt, BASE_RECEIPT_SHA256, maximum=2 * 1024 ** 2)
    data, wheel, base = map(json.loads, (data_raw, wheel_raw, base_raw))
    if base["image"] != BASE or base["image_id"] != BASE_ID:
        raise ValueError("Base identity differs from the reviewed receipt")
    packages = {normalize(k): v for k, v in base["validation"]["packages"].items()}
    if len(packages) != 45 or any(packages.get(k) != v for k, v in PRESERVED_RUNTIME.items()):
        raise ValueError("Base dependency closure changed")
    if set(RUNTIME_ADDITIONS) & packages.keys():
        raise ValueError("Science5 additions must not replace base distributions")
    selected = [row for row in wheel["files"] if normalize(row["package"]) in RUNTIME_ADDITIONS]
    if len(selected) != 2 or len({normalize(row["package"]) for row in selected}) != 2:
        raise ValueError("Exactly two reviewed runtime wheels are required")
    payloads = {}
    for row in selected:
        name = normalize(row["package"])
        if (row["version"] != RUNTIME_ADDITIONS[name] or row["sha256"] != WHEEL_PINS[name]
                or not row["url"].startswith("https://files.pythonhosted.org/packages/")):
            raise ValueError("Runtime wheel identity changed")
        filename = relative(row["filename"])
        if "/" in filename or not filename.endswith(".whl"):
            raise ValueError("Expected a wheel basename")
        payloads["wheels/" + filename] = read(checked_path(wheels) / filename, row["sha256"], row["bytes"])
    if len(data["files"]) != 9 or set(data["task_details"]) != set(TASKS):
        raise ValueError("Data lock must describe exactly the five reviewed tasks and nine files")
    paths = set()
    for row in data["files"]:
        name = relative(row["path"])
        if name in paths or row["role"] != "runtime_data":
            raise ValueError("Data lock contains duplicate or non-runtime files")
        paths.add(name)
        payloads["data/" + name] = read(checked_path(cache_root) / name, row["sha256"], row["bytes"])
    return data_raw, base_raw, packages, selected, payloads


def smoke_script():
    """Installed UID998 smoke: imports and integrity only, never folding or a seed."""
    return '''import hashlib, importlib.metadata, json, os, pathlib, re, stat, subprocess, sys
root = pathlib.Path("/opt/arena-science5-support")
expected = json.loads((root / "expected-packages.json").read_bytes())
actual = {re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower(): d.version
          for d in importlib.metadata.distributions()}
assert actual == expected, "Full base/addition dependency closure changed"
assert sys.version_info[:2] == (3, 11)
subprocess.run([sys.executable, "-m", "pip", "check"], check=True)
import RNA, rdkit, numpy, scipy, PIL
assert RNA.__version__ == "2.6.4" and rdkit.__version__ == "2026.03.6"
assert (numpy.__version__, scipy.__version__, PIL.__version__) == ("2.2.6", "1.15.3", "12.3.0")
raw = (root / "data-lock.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == "DATA_SHA"
lock = json.loads(raw)
data = pathlib.Path("/opt/arena-science5-data")
assert os.environ["ARENA_TASK_CACHE_DIR"] == str(data)
found = set()
for path in data.rglob("*"):
    info = path.lstat()
    assert not path.is_symlink() and not info.st_mode & 0o222
    if path.is_file(): found.add(path.relative_to(data).as_posix())
    else: assert stat.S_ISDIR(info.st_mode)
assert found == {r["path"] for r in lock["files"]}
for row in lock["files"]:
    value = (data / row["path"]).read_bytes()
    assert len(value) == row["bytes"] and hashlib.sha256(value).hexdigest() == row["sha256"]
assert os.getuid() in (0, 998)
print(json.dumps({"schema": "arena.science5-image-smoke/1", "uid": os.getuid(),
    "packages": actual, "data_files_verified": len(found), "model_calls": 0,
    "candidate_evaluations": 0, "readiness": "imports_and_data_only"}, sort_keys=True))
'''.replace("DATA_SHA", DATA_LOCK_SHA256)


def install_script():
    return '''import os, pathlib, shutil, subprocess, sys
recipe = pathlib.Path("/recipe")
data = pathlib.Path("/opt/arena-science5-data")
support = pathlib.Path("/opt/arena-science5-support")
assert not data.exists() and not support.exists()
subprocess.run([sys.executable, "-m", "pip", "--isolated", "install", "--no-index",
    "--no-deps", "--require-hashes", "--find-links=/recipe/wheels",
    "-r", "/recipe/requirements.lock"], check=True)
shutil.copytree(recipe / "data", data)
support.mkdir(mode=0o755)
for name in ("data-lock.json", "expected-packages.json", "smoke.py"):
    shutil.copyfile(recipe / name, support / name)
for root in (data, support):
    for path in root.rglob("*"): path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)
os.environ["ARENA_TASK_CACHE_DIR"] = str(data)
subprocess.run([sys.executable, "-B", str(support / "smoke.py")], check=True)
'''


def review_plan():
    return f'''Science5 image recipe: review only; no image or seed has been run.

Base repository digest: {BASE}
Base local image ID: {BASE_ID}
Inspect both identities, Entrypoint=null, Cmd=["python3"], Linux/amd64 before build.
Recheck recipe.json file hashes before using the immutable private context.
The 45 base distributions remain exact. Only ViennaRNA2.6.4 and RDKit2026.3.6
are installed from the two hash-locked official CPU wheels. Pillow12.3.0,
NumPy2.2.6 and SciPy1.15.3 stay unchanged. No pip resolution/download, source
compilation, CUDA, h5py, netCDF4, cftime or other prep packages are added.

Proposed separately approved build sequence:
1. Create one uniquely named Docker runc container from the exact base, --pull never,
   --user 0:0, --network none, --cpus 2, --memory 8g --memory-swap 8g,
   --pids-limit 256, --cap-drop ALL, --security-opt no-new-privileges.
   Mount this context read-only at /recipe; use no source, sockets or credentials.
   Set OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1, MKL_NUM_THREADS=1,
   NUMEXPR_NUM_THREADS=1, PYTHONDONTWRITEBYTECODE=1.
   Command: python3 -B /recipe/install.py. Preserve exit code and complete log.
2. Commit only after exit0 and exact dependency/data smoke success. Explicitly set
   ENTRYPOINT [], CMD ["python3"], ENV ARENA_TASK_CACHE_DIR={DATA_ROOT},
   the four thread variables=1, PYTHONDONTWRITEBYTECODE=1. Set data-lock,
   requirements-lock, recipe and base identity labels. Use a new private tag.
3. Inspect the resulting immutable image ID. Run python3 -B
   {SUPPORT_ROOT}/smoke.py as UID998:998 from that exact ID,
   --network none --read-only, 2CPU/8GiB/256PID, no capabilities/GPU or host mounts,
   --tmpfs /tmp:rw,nosuid,nodev,size=268435456. Require complete closure47,
   RNA import2.6.4, RDKit import2026.03.6, all nine files and read-only permissions.
4. Publish only to the private registry, bind the unique repository digest to that
   image ID, retain inspect/log hashes and recipe receipt. Remove only the uniquely
   named build/smoke containers; on uncertain cleanup preserve explicit evidence.
5. Independent review must bind science5 IMAGE/IMAGE_ID to the resulting immutable
   build before runtime admission. The old science8 image/profile stays intact.

Subsequent canonical seed checks are a separate step, not authorized by this file.
Proposed {RESOURCE_PROFILE}:1CPU/4GiB/256PID, control cgroup required,
600s for Pantheon/ProteinGym/Eterna/OceanBench; original180s for GEOM.
No timeout/cut/shape/budget reduction; unchanged seed/evaluator/library receipt.
Only fresh valid canonical receipts on the new image can establish seed readiness.
Keep all959 tasks in future inventories; select only these5 in this opt-in group.
Native confirmation and campaign admission remain additional evidence gates.
These are recreated benchmark protocols, not claims of current SOTA or paper
reproduction. Original source/derived hashes and all scientific cuts are unchanged.
'''


def prepare(*, data_lock, cache_root, base_receipt, wheel_lock, wheels, output):
    output = checked_path(output)
    if output.exists():
        raise ValueError("Output must be a new private directory")
    for path in (data_lock, cache_root, base_receipt, wheel_lock, wheels):
        path = checked_path(path)
        if output.is_relative_to(path) or path.is_relative_to(output):
            raise ValueError("Output must be separate from every input tree")
    data, base, packages, selected, payloads = inputs(data_lock, cache_root, base_receipt, wheel_lock, wheels)
    lock = "".join(f"{normalize(r['package'])}=={r['version']} --hash=sha256:{r['sha256']}\n"
                   for r in sorted(selected, key=lambda row: normalize(row["package"])))
    payloads.update({"data-lock.json": data, "base-receipt.json": base,
                     "requirements.lock": lock.encode(), "install.py": install_script().encode(),
                     "smoke.py": smoke_script().encode(), "PLAN.txt": review_plan().encode(),
                     "expected-packages.json": encode({**packages, **RUNTIME_ADDITIONS})})
    plan = {"schema": "arena.science5-image-recipe/1", "profile": PROFILE, "group": GROUP,
            "base": BASE, "base_image_id": BASE_ID, "base_receipt_sha256": BASE_RECEIPT_SHA256,
            "base_package_count": len(packages), "added_packages": RUNTIME_ADDITIONS,
            "data_lock_sha256": DATA_LOCK_SHA256, "wheel_source_lock_sha256": WHEEL_LOCK_SHA256,
            "data_files": 9, "model_calls": 0, "candidate_evaluations": 0, "image_built": False,
            "canonical_readiness": "pending", "build_resources": {"cpus": 2, "memory_mb": 8192, "pids": 256},
            "install_network": "none", "runtime_data_root": DATA_ROOT,
            "proposed_seed_resource_profile": RESOURCE_PROFILE,
            "task_timeouts": {name: value["timeout"] for name, value in TASKS.items()},
            "files": {name: {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
                      for name, raw in sorted(payloads.items())}}
    output.mkdir(mode=0o700, parents=True)
    for name, raw in {**payloads, "recipe.json": encode(plan)}.items():
        path = output / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(raw)
        path.chmod(0o600)
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("data-lock", "cache-root", "base-receipt", "wheel-lock", "wheels", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    plan = prepare(**vars(args))
    print(json.dumps({"recipe": str(args.output / "recipe.json"), "image_built": plan["image_built"],
                      "canonical_readiness": plan["canonical_readiness"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
