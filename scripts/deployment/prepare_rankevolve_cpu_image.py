#!/usr/bin/env python3
"""Prepare one offline, full-dataset RankEvolve image context; never run Docker.

Reviewed private data is not canonical readiness. The source tree and its task
locks remain untouched; only explicitly pinned runtime data enters the context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

RUNTIME_IMAGE = "sha256:40faa5a249d3acc8db356e48b774c6be26ca337ac30e1cf497754c3b76d25176"
PRIVATE_IMAGE = "sha256:61cb5b24318727000c985b31aa65088f3baf61c7348a8f6e649a04893e308c0f"
SOURCE_COMMIT = "8f664bcd5123bac2397f0c1bfbdb347ca3233483"
ARENA_SOURCE_BASELINE = "8c6871fc925f25b20d77295f1ae7bed4f4ca3f90"
PRIVATE_CLOSURE_SHA256 = "0edcc43ecc67a5c64cd27d71a22e9a3b933577cf36dbc7508e840072cd8e81d4"
REQUIREMENTS_SHA256 = "5bed76b623433e3517748688743fa4f7a11fb115c5e6b969e892d9fc24eb3c8e"
WHEELS_SHA256 = "467272b0b92b313fc4f1680f28e4f6bcf8c384efe84d3bd3e4f28694db799347"
SEED_SHA256 = "423084a12afd49b21b558848b47de6fe8475f8493c9dfe4f1a707d08ceeca473"
EVALUATOR_SHA256 = "66ea7204af06a0b45af24cf6931e68a4a10aceee862dc92ce0a0d3b6f6d1dc39"
FILES = ("public/corpus.jsonl", "public/queries.jsonl", "private/qrels.jsonl")
DATASETS = {
    "scidocs": (25657, 1000, 900), "trec-covid": (171332, 50, 3600),
    "climate-fever": (5416593, 1535, 14400), "fiqa": (57638, 648, 3600),
    "webis-touche2020": (382545, 49, 3600), "quora": (522931, 10000, 3600),
    "cqadupstack": (457199, 13145, 3600), "dbpedia-entity": (4635922, 400, 14400),
    "nq": (2681468, 3452, 14400), "hotpotqa": (5233329, 7405, 14400),
    "fever": (5416568, 6666, 14400), "dl19": (8841823, 200, 14400),
    "dl20": (8841823, 200, 14400),
}
PROBLEM_PINS = {
    "scidocs": "f58bf90fdc5f2a84223f9c3e4f0ad2a9836ec53bf4aa6ddf8ff5b62437766fcf",
    "trec-covid": "37ac8b71395d45ea329efb1885ca51775630b654b6636c578b1380353ccf5e04",
    "climate-fever": "61ee3ecc0153abd40be7fc32d9a9526fa00bc1203316be8abfa5dd4471dd9493",
    "fiqa": "534dfa83cacad6547f8b661f2cbc8c154fff14b73ee8e686e85a1866d1c96c09",
    "webis-touche2020": "e397d221282d1364524c5b2222b3bd376c2710ad5a55d530dcc5a8c917dcb88e",
    "quora": "5063210754d69cdc80177fe05399a36010039319dd3b28429e8ecae20ec5a8b3",
    "cqadupstack": "46e85a6df6bbe71e8fc18404873fbf4507689271a8e4966b3caf906de34f6d4d",
    "dbpedia-entity": "5aab58e0cf5d42958f523af60b507dbfde5c4118caf6af4da7083346d3390639",
    "nq": "fd822502565288924d4175e9fd8a6256d7be44a27a1f6c032d82312e7ef24afb",
    "hotpotqa": "e4f3a63862f85075497a0f7d99630e41d4a439c89c4df9e03a8c6990434c625b",
    "fever": "32c7915b803ce73dc6765201b749fafca1d99456b2709a9c3fb4e843e629f1e1",
    "dl19": "f9a953783ef6376053fb3c40f4e8d7a7add9f4b7002dce65c6579663d52333cb",
    "dl20": "5875b04dfc1eea3d894806960e68c5611728cf236fcee6da50cd346add1db59c",
}
# Reviewed full-data hashes, not image pins or canonical execution receipts.
DATA_PINS = {
    "scidocs": "5411cea102e24cc6b7af6884845c1f45bb8e5d3e718ddd394cfbd713e19d3a2f",
    "trec-covid": "8ff87a981142bc0fc6746c2d42d4ce2c5222b94143c780dc0b81219dcd2e0077",
    "climate-fever": "4614d0e4137147a18f3a73e1aa75e3b555ba7d763dec948e85e282f34ae8a342",
    "fiqa": "381625a2189300df19c2484e3ab56f70aeab7d1b8a8761395f3d87f1ec204db3",
    "quora": "9473b9dee16732668860106995a6cdb167443358ee0f315084048477c3672186",
    "webis-touche2020": "f93822d7455b73af70cbb21d558b4cc13d8650694c09cde16b8006c48218d6e0",
    "cqadupstack": "808dc7a6867004a986e57b0cb96aa4d7844cafd5bb64a4307decd6c9e3697d68",
    "dbpedia-entity": "0594f136f235501401808d2b3acdf3f4866c6f0c5981c6a1b43292dc0e5e3b2d",
    "nq": "f8c18ea535fe5676091d2afe934f43e163293bd997b21b7ac4d48d2451f80e5b",
}
LOCK_PINS = {
    "scidocs": "acaef6156a80ceab4a7f512ad5111ed1881c0fb2310c9aeaf0485339ff0f5b47",
    "trec-covid": "07e0787ba95eecf9bd015880f8ac78bfa41f1be7368467d796ae48765952139e",
    "climate-fever": "aee9fc477974d8d50475f70a2bdce056020f32f7df9482af96e85cc083112a16",
    "fiqa": "32d05f8650ed7a002c38b4b4b7fbcc63770e0e1c2993f8c03fbdeb26c42b094e",
    "quora": "69577f1c24d8a0b9df319c517a2b7bafebf088c2fe787f7c0cd012b3011dcacd",
    "webis-touche2020": "57335fece41bf05451076d5d1a85bd7fa699a2ee4f2894e2fb9a14de5c6d49e7",
    "cqadupstack": "1cd74933493ce9f8a4f9c5b8c9d90175993e368d8b375c0747b4e90c0a963e05",
    "dbpedia-entity": "029182ebca8df89572fdc8008e6683e2e71ca8cbfd236aaa19efc57c77e023c8",
    "nq": "0240fb527175538b9deba9109769949a9e88760cebd7b78d05ccef11d60d6812",
}
HELPERS = {
    "rankevolve/__init__.py": "08fe0d1c2f4b667a7a21cf4800ab992fc266e1e07a632d48565be58a03e20abf",
    "rankevolve/candidate.py": "47517ce0ab8501f9b7e153cb3d3136deb10082cd1c5da78bcd6bb8289931102a",
    "rankevolve/contract.py": "1bac1f469ba6b5b3cc1ae3d4dd3bf55e10ec9386541f54c9ae3cf83a58a0e2ef",
    "rankevolve/evaluator.py": "180bed62d96cd6d1fb5eb69e8c4bb558bcc364d470f42c892d7ba320a30700ee",
    "rankevolve/metrics.py": "dfaa7d629911f1176ddf7e6a54ad8230b35e46e7fce4c24774192257d3f2cd49",
    "rankevolve/prepare.py": "681dc343ae7a596aefb8a771f65ed77eef65f9a7e3aaed5aa35d85163913edd8",
    "rankevolve/ranking.py": "ea6a8a8343ae01fde3250a473c206bcec174eee11f588d681a8dee21a1757610",
    "rankevolve/seed_library.py": "6112f2ab541074a65e431a7b3e624814630f906b2ca26998ffaa7307efb06cc2",
    "autoresearch_suite/__init__.py": "54e80b2666bf9df10a140b4ee0f0623799bec01d01e8221bd67e647687a7ff8a",
    "autoresearch_suite/runtime.py": "e5274a3bab8202885a7d57e009e8f74075fc206d0f52c70cf5ce917f7f1a4248",
}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def decoded(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("Nonfinite JSON value")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def path_checked(value):
    path = Path(value)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("Use absolute paths without symlinks or traversal")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Symlinked paths are forbidden")
    return path


def opened(value):
    """Open through directory descriptors: no symlink in any path component."""
    path = path_checked(value)
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in path.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    finally:
        os.close(descriptor)
    handle = os.fdopen(file, "rb")
    if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
        handle.close()
        raise ValueError("Expected a regular input file")
    return handle


def read(value, expected, maximum=4 * 1024 ** 2):
    with opened(value) as handle:
        if os.fstat(handle.fileno()).st_size > maximum:
            raise ValueError("Input exceeds its size bound")
        raw = handle.read(maximum + 1)
    if len(raw) > maximum or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Input SHA256 differs from the reviewed pin")
    return raw


def roster():
    return [{"task_id": "rankevolve-" + name, "dataset": name,
             "documents": values[0], "queries": values[1], "candidate_timeout_seconds": values[2],
             "data_manifest_sha256": DATA_PINS.get(name), "image_id": None,
             "data_status": "reviewed_full_data_pin" if name in DATA_PINS else "preparation_pending",
             "canonical_readiness": "pending"} for name, values in DATASETS.items()]


def runtime_inputs(runtime_config, runtime_root, runtime_image):
    if runtime_image != RUNTIME_IMAGE:
        raise ValueError("Use the exact reviewed RankEvolve runtime image")
    # Docker image IDs are SHA256 of these original config bytes, not inspect JSON.
    raw = read(runtime_config, RUNTIME_IMAGE.removeprefix("sha256:"))
    config = decoded(raw)
    image = config.get("config", {})
    if (config.get("os") != "linux" or config.get("architecture") != "amd64"
            or image.get("Entrypoint") not in (None, []) or image.get("Cmd") != ["python3"]
            or image.get("User", "") != "" or image.get("WorkingDir", "") != ""):
        raise ValueError("Runtime platform or command contract changed")
    env = image.get("Env", [])
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "BM25_QUERY_WORKERS"):
        if [item for item in env if item.startswith(name + "=")] != [name + "=1"]:
            raise ValueError("Runtime thread policy changed")
    proof = {"image_id": RUNTIME_IMAGE, "config_sha256": hashlib.sha256(raw).hexdigest(),
             "rootfs": config["rootfs"], "labels": image.get("Labels"),
             "related_private_data_image": PRIVATE_IMAGE,
             "dependencies": {"numpy": "2.3.1", "scipy": "1.16.3"}}
    return proof, {"requirements.lock": read(runtime_root / "requirements.lock", REQUIREMENTS_SHA256),
                   "wheels.json": read(runtime_root / "wheels.json", WHEELS_SHA256)}


def source_inputs(source_root, dataset):
    pins = {"suite/_lib/" + name: value for name, value in HELPERS.items()}
    prefix = "suite/rankevolve-" + dataset + "/"
    pins.update({prefix + "initial_program.py": SEED_SHA256, prefix + "evaluator.py": EVALUATOR_SHA256,
                 prefix + "problem.json": PROBLEM_PINS[dataset]})
    for name, digest in pins.items():
        read(source_root / name, digest)
    return {"arena_source_baseline": ARENA_SOURCE_BASELINE, "upstream_commit": SOURCE_COMMIT,
            "private_original_closure_sha256": PRIVATE_CLOSURE_SHA256, "files": pins}


def dataset_inputs(dataset, data_root, data_lock):
    if dataset not in DATA_PINS:
        raise ValueError("Full data preparation and reviewed manifest are pending")
    lock_raw = read(data_lock, LOCK_PINS[dataset])
    lock = decoded(lock_raw)
    docs, queries, timeout = DATASETS[dataset]
    if (lock.get("schema") != "arena.rankevolve-task-data/1" or lock.get("dataset") != dataset
            or lock.get("manifest_sha256") != DATA_PINS[dataset]
            or type(lock.get("candidate_timeout_seconds")) is not int
            or lock["candidate_timeout_seconds"] != timeout):
        raise ValueError("Task data-lock identity or original timeout changed")
    raw = read(data_root / "manifest.json", DATA_PINS[dataset])
    manifest = decoded(raw)
    expected = {"schema": "arena.rankevolve-data/1", "dataset": dataset, "source_commit": SOURCE_COMMIT,
                "documents": docs, "queries": queries, "sample_queries": 0, "warmup_queries": 0,
                "tokenizer": "candidate.LuceneTokenizer", "search_protocol": "exploratory_search_on_test",
                "qrels_semantics": "positive relevance is binary; no graded gain"}
    if any(type(manifest.get(k)) is not type(v) or manifest[k] != v for k, v in expected.items()):
        raise ValueError("Full dataset counts or protocol changed")
    files = manifest.get("files")
    if type(files) is not dict or set(files) != set(FILES):
        raise ValueError("Manifest must bind exactly the three runtime data files")
    for row in files.values():
        if (type(row) is not dict or set(row) != {"bytes", "sha256"}
                or type(row["bytes"]) is not int or row["bytes"] <= 0
                or type(row["sha256"]) is not str or len(row["sha256"]) != 64):
            raise ValueError("Invalid data file hash/size contract")
    return raw, lock_raw, manifest


def copy_data(source, destination, expected, rows):
    """Stream full corpora; count original records while verifying copied bytes."""
    digest, count, size, last = hashlib.sha256(), 0, 0, b""
    with opened(source) as incoming, destination.open("xb") as target:
        if os.fstat(incoming.fileno()).st_size != expected["bytes"]:
            raise ValueError("Data size differs from manifest")
        for block in iter(lambda: incoming.read(1024 ** 2), b""):
            size += len(block)
            if size > expected["bytes"]:
                raise ValueError("Data grew beyond its locked size")
            target.write(block)
            digest.update(block)
            count += block.count(b"\n")
            last = block[-1:]
    if (size != expected["bytes"] or digest.hexdigest() != expected["sha256"]
            or count != rows or last != b"\n"):
        raise ValueError("Data hash, full record count or final newline differs")
    destination.chmod(0o444)
    return {**expected, "records": count}


def smoke_script():
    return '''import hashlib, json, pathlib, stat
import numpy, scipy
assert (numpy.__version__, scipy.__version__) == ("2.3.1", "1.16.3")
support = pathlib.Path("/opt/arena-rankevolve-image")
expected = json.loads((support / "expected-data.json").read_bytes())
base = pathlib.Path("/opt/arena-data/rankevolve")
found = set()
for path in base.rglob("*"):
    info = path.lstat()
    assert not path.is_symlink() and not info.st_mode & 0o222
    if stat.S_ISREG(info.st_mode): found.add(path.relative_to(base).as_posix())
    else: assert stat.S_ISDIR(info.st_mode)
assert found == set(expected)
for name, row in expected.items():
    digest, size, count = hashlib.sha256(), 0, 0
    with (base / name).open("rb") as source:
        for block in iter(lambda: source.read(1024**2), b""):
            digest.update(block); size += len(block); count += block.count(b"\\n")
    assert size == row["bytes"] and digest.hexdigest() == row["sha256"]
    if "records" in row: assert count == row["records"]
print(json.dumps({"schema":"arena.rankevolve-image-smoke/1", "files_verified":len(found),
    "candidate_evaluations":0, "model_calls":0, "readiness":"data_and_imports_only"}))
'''


def prepare(*, dataset, source_root, data_root, data_lock, runtime_config, runtime_root,
            output, runtime_image=RUNTIME_IMAGE):
    if dataset not in DATASETS:
        raise ValueError("Unknown RankEvolve dataset")
    paths = [path_checked(p) for p in (source_root, data_root, data_lock, runtime_config, runtime_root)]
    source_root, data_root, data_lock, runtime_config, runtime_root = paths
    output = path_checked(output)
    if output.exists() or any(output.is_relative_to(p) or p.is_relative_to(output) for p in paths):
        raise ValueError("Output must be new and separate from every input")
    runtime, runtime_files = runtime_inputs(runtime_config, runtime_root, runtime_image)
    source = source_inputs(source_root, dataset)
    manifest_raw, lock_raw, manifest = dataset_inputs(dataset, data_root, data_lock)
    # Use a sibling temporary tree: a failed hash/count check publishes no recipe.
    with tempfile.TemporaryDirectory(prefix=".rankevolve-image-", dir=output.parent) as temporary:
        stage = Path(temporary)
        bundle = stage / "data" / dataset
        for name in ("public", "private"):
            (bundle / name).mkdir(mode=0o700, parents=True)
        expected = {}
        counts = (manifest["documents"], manifest["queries"],
                  {"dl19": 43, "dl20": 54}.get(dataset, manifest["queries"]))
        for name, count in zip(FILES, counts):
            expected[dataset + "/" + name] = copy_data(data_root / name, bundle / name, manifest["files"][name], count)
        expected[dataset + "/manifest.json"] = {"sha256": DATA_PINS[dataset], "bytes": len(manifest_raw)}
        (bundle / "manifest.json").write_bytes(manifest_raw)
        (bundle / "manifest.json").chmod(0o444)
        support = {**runtime_files, "runtime-proof.json": encoded(runtime), "source-proof.json": encoded(source),
                   "task-data-lock.json": lock_raw, "expected-data.json": encoded(expected),
                   "smoke.py": smoke_script().encode()}
        (stage / "support").mkdir(mode=0o700)
        for name, raw in support.items():
            (stage / "support" / name).write_bytes(raw)
            (stage / "support" / name).chmod(0o444)
        dockerfile = (f"FROM {RUNTIME_IMAGE}\nCOPY data/ /opt/arena-data/rankevolve/\n"
                      "COPY support/ /opt/arena-rankevolve-image/\n"
                      "RUN python3 -B /opt/arena-rankevolve-image/smoke.py\n")
        included = ["Dockerfile", "data/", f"data/{dataset}/", f"data/{dataset}/public/",
                    f"data/{dataset}/private/", "support/",
                    *("data/" + name for name in expected), *("support/" + name for name in support)]
        small = {"Dockerfile": dockerfile.encode(), ".dockerignore": ("*\n" + "\n".join("!" + n for n in included) + "\n").encode()}
        for name, raw in small.items():
            (stage / name).write_bytes(raw)
            (stage / name).chmod(0o600)
        for p in (stage / "data", bundle, bundle / "public", bundle / "private", stage / "support"):
            p.chmod(0o555)
        file_map = {"data/" + n: v for n, v in expected.items()}
        file_map.update({"support/" + n: {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in support.items()})
        file_map.update({n: {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for n, b in small.items()})
        plan = {"schema": "arena.rankevolve-image-recipe/1", "task_id": "rankevolve-" + dataset,
                "runtime": runtime, "source": source, "data_manifest_sha256": DATA_PINS[dataset],
                "task_data_lock_sha256": LOCK_PINS[dataset], "data_source": manifest["source"],
                "roster": roster(), "files": file_map, "image_built": False, "image_id": None,
                "canonical_readiness": "pending", "candidate_evaluations": 0, "model_calls": 0,
                "build_network": "none", "build_resources": {"cpus": 2, "memory_mb": 8192, "pids": 256},
                "inherited_labels": "preserved; require exact CPU recovery binding before admission",
                "next_gate": "review recipe, bounded offline build, UID998 data smoke, fresh canonical seed"}
        (stage / "recipe.json").write_bytes(encoded(plan))
        (stage / "recipe.json").chmod(0o600)
        # Docker COPY includes timestamps: freeze them as well as file contents.
        for p in stage.rglob("*"):
            os.utime(p, (0, 0), follow_symlinks=False)
        stage.rename(output)
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--dataset", choices=tuple(DATASETS))
    for name in ("source-root", "data-root", "data-lock", "runtime-config", "runtime-root", "output"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args(argv)
    if args.inventory:
        print(encoded(roster()).decode(), end="")
        return 0
    values = vars(args)
    values.pop("inventory")
    if any(value is None for value in values.values()):
        parser.error("All context input paths and --dataset are required")
    plan = prepare(**values)
    print(json.dumps({"recipe": str(args.output / "recipe.json"), "image_built": plan["image_built"],
                      "canonical_readiness": plan["canonical_readiness"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
