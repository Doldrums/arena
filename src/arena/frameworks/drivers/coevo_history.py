"""Observational native-save sidecars for the next CoEvo adapter profile.

No optimizer state, evaluator, retry, selection or native write is replaced.
The sidecar snapshots bytes after the real RunStore save, before a later save
can overwrite the same native generation filename. No pickle is loaded.
"""
from __future__ import annotations

from contextlib import contextmanager
import functools
import hashlib
import inspect
from itertools import islice
import json
import os
from pathlib import Path
import re
import stat

from arena.evaluator_proxy import directory_fd, read_regular

COMMIT = "dcad65e9799961cf67cf29865ff41dda2902a808"
SOURCE_HASHES = {
    "CoEvo/src/coevo/core/coevo_method.py": "41482e7245bbc1b210bbb1eb1649d8d391e1e51a4eec5cd54dd1de35402b8872",
    "main_run.py": "3024283a03a6a4eeda5e55668518b3a81b02545423c54df13f883da5b6fadbf4",
}
DEPENDENCY_HASHES = {
    "core/method.py": "04d0b0d7ca506c1eb3d479aa2e1d72d96001d7c2f3871b3b45707c5e546b08d6",
    "core/store.py": "1f1b6ce8c5148755f885a2402096fc0dc4cff899e2848288ea71f5a6220ca03b",
    "core/solution.py": "cd2134a5cf404b8094eeff81dd607245274af0d763f2955e0baaef377da7576f",
}
MAX_HISTORY = 8 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_SAVES = 100


def _read(path, maximum):
    fd = directory_fd(Path(path).absolute().parent)
    try: return read_regular(fd, Path(path).name, maximum)
    finally: os.close(fd)


def _decode(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise ValueError("Duplicate native JSON key")
            out[key] = value
        return out
    # Native RunStore serializes invalid scores as -Infinity. They are retained
    # in raw snapshots and fingerprints, never converted into finite metrics.
    return json.loads(raw, object_pairs_hook=pairs)


def project_history(raw):
    if len(raw) > MAX_HISTORY: raise ValueError("CoEvo history exceeds 8 MiB")
    value = _decode(raw)
    if (type(value) is not dict or type(value.get("generation")) is not int or value["generation"] < 0
            or type(value.get("solutions")) is not list or len(value["solutions"]) > 10000
            or type(value.get("usage")) is not list or len(value["usage"]) > 10000):
        raise ValueError("Invalid native generation history")
    groups = {}
    for index, row in enumerate(value["solutions"]):
        if type(row) is not dict or not {"sol_string", "metadata", "evaluation_res"} <= row.keys():
            raise ValueError("Invalid native registered solution row")
        identity = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=True).encode()).hexdigest()
        groups.setdefault(identity, []).append(index)
    return {"native_generation": value["generation"],
            "native_history_rows": len(value["solutions"]),
            "distinct_registered_records": len(groups),
            "duplicate_registered_rows": len(value["solutions"]) - len(groups),
            "native_usage_records": len(value["usage"]),
            "nonempty_native_usage_records": sum(bool(item) for item in value["usage"]),
            "task_evaluation_calls": None, "physical_model_requests": None,
            "record_groups": [{"sha256": key, "row_indices": indices} for key, indices in groups.items()],
            "count_semantics": "Distinct records compare the full serialized native solution, including chain metadata; they are not physical evaluations, unique programs, or model calls."}


def verify_sources(workspace, dependency_root):
    evidence = {"repository_commit": COMMIT, "repository_files": {}, "evotoolkit_version": "1.0.2", "dependency_files": {}}
    for root, expected, key in ((Path(workspace), SOURCE_HASHES, "repository_files"),
                                (Path(dependency_root), DEPENDENCY_HASHES, "dependency_files")):
        for name, digest in expected.items():
            # uv legitimately hardlinks immutable installed package source into
            # its cache. Source hashing may read those regular files; mutable
            # run artifacts still use the stricter single-link reader above.
            path = (root / name).absolute()
            parent = directory_fd(path.parent)
            try:
                descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                with os.fdopen(descriptor, "rb") as stream:
                    before = os.fstat(stream.fileno())
                    if not stat.S_ISREG(before.st_mode) or before.st_size > 1024 * 1024:
                        raise ValueError("Invalid CoEvo observation source file")
                    raw = stream.read(1024 * 1024 + 1); after = os.fstat(stream.fileno())
                    signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                    if len(raw) > 1024 * 1024 or signature(before) != signature(after):
                        raise ValueError("CoEvo observation source changed during hashing")
            finally: os.close(parent)
            actual = hashlib.sha256(raw).hexdigest()
            if actual != digest: raise ValueError("CoEvo observation source hash changed: " + name)
            evidence[key][name] = digest
    return evidence


def _write_new(directory, name, raw):
    fd = directory_fd(directory)
    try:
        target = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(target, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.fsync(fd)
    finally: os.close(fd)


class HistoryArchive:
    """One synchronous native RunStore; sequence identifies saves, not generations."""
    def __init__(self, workspace, store, source_evidence):
        self.workspace = Path(workspace).resolve()
        self.store = store
        self.source_evidence = source_evidence
        self.output = Path(store.output_path).absolute()
        if not self.output.is_relative_to(self.workspace):
            raise ValueError("CoEvo output is outside its isolated workspace")
        parent = directory_fd(self.output)
        try: os.mkdir("arena-history", 0o700, dir_fd=parent)
        finally: os.close(parent)
        self.directory = self.output / "arena-history"
        self.sequence = 0; self.total = 0

    def record(self, native_generation):
        if type(native_generation) is not int or native_generation < 0 or self.sequence >= MAX_SAVES:
            raise ValueError("Invalid or exhausted CoEvo save sequence")
        native_path = Path(self.store.history_dir).absolute() / f"gen_{native_generation}.json"
        if not native_path.is_relative_to(self.output): raise ValueError("Native history path left its output")
        raw = _read(native_path, MAX_HISTORY)
        if self.total + len(raw) > MAX_TOTAL: raise ValueError("CoEvo sidecar exceeds 128 MiB")
        projection = project_history(raw)
        if projection["native_generation"] != native_generation: raise ValueError("Native saved generation differs")
        basename = f"save_{self.sequence:06d}"
        relative = (self.directory / (basename + ".native.json")).relative_to(self.workspace).as_posix()
        receipt = {"schema": "arena.coevo-save/1", "sequence": self.sequence,
                   "native_generation": native_generation, "native_path": native_path.relative_to(self.workspace).as_posix(),
                   "snapshot": {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
                   "source": self.source_evidence, "native_state_modified": False,
                   "canonical_evaluation": False, "accounting": projection}
        _write_new(self.directory, basename + ".native.json", raw)
        _write_new(self.directory, basename + ".receipt.json",
                   (json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
        self.sequence += 1; self.total += len(raw)
        return receipt


@contextmanager
def capture_saves(store_class, workspace, source_evidence):
    """Wrap only persistence; delegate the original method exactly once."""
    original = store_class.save_generation_history
    archives = {}

    @functools.wraps(original)
    def saved(store, generation, solutions, usage, statistics=None):
        value = original(store, generation, solutions, usage, statistics)
        # Keep stores alive: Python object-id reuse cannot merge two sequences.
        entry = archives.get(id(store))
        if entry is None:
            entry = (store, HistoryArchive(workspace, store, source_evidence))
            archives[id(store)] = entry
        entry[1].record(generation)
        return value

    store_class.save_generation_history = saved
    try: yield
    finally: store_class.save_generation_history = original


@contextmanager
def observe_native_saves(workspace):
    """Import only on explicit v2 execution, after normal native setup."""
    from importlib.metadata import version
    from evotoolkit.core.store import RunStore
    if version("evotoolkit") != "1.0.2": raise ValueError("CoEvo v2 observation requires evotoolkit 1.0.2")
    dependency_root = Path(inspect.getfile(RunStore)).resolve().parents[1]
    evidence = verify_sources(workspace, dependency_root)
    with capture_saves(RunStore, workspace, evidence): yield


def read_sidecars(output_dir):
    """Read only run-relative JSON/hash evidence; never load checkpoints."""
    output = Path(output_dir).resolve()
    workspace = output / "workspace/coevo-observed-v2"
    value = {"schema": "arena.coevo-accounting/1", "canonical_evaluation": False,
             "status": "missing", "saves": [], "artifacts": [], "warnings": [],
             "task_evaluation_calls": None, "physical_model_requests": None}
    try:
        paths = sorted(islice(workspace.glob("results/*/arena-history/save_*.receipt.json"), MAX_SAVES + 1))
        if len(paths) > MAX_SAVES: raise ValueError("Too many native save receipts")
        snapshots = list(islice(workspace.glob("results/*/arena-history/save_*.native.json"), MAX_SAVES + 1))
        if set(snapshots) != {p.with_name(p.name.replace(".receipt.json", ".native.json")) for p in paths}:
            raise ValueError("Unpaired native history snapshot or receipt")
        sequences = {}; total = 0
        expected_evidence = {"repository_commit": COMMIT, "repository_files": SOURCE_HASHES,
                             "evotoolkit_version": "1.0.2", "dependency_files": DEPENDENCY_HASHES}
        for path in paths:
            raw = _read(path, 1024 * 1024); receipt = _decode(raw)
            sequence = receipt.get("sequence")
            if (receipt.get("schema") != "arena.coevo-save/1" or type(sequence) is not int
                    or sequence != sequences.get(path.parent, 0)
                    or path.name != f"save_{sequence:06d}.receipt.json"
                    or receipt.get("source") != expected_evidence
                    or receipt.get("native_state_modified") is not False):
                raise ValueError("Invalid CoEvo sidecar provenance or sequence")
            snapshot = path.with_name(f"save_{sequence:06d}.native.json")
            native = _read(snapshot, MAX_HISTORY); total += len(native)
            if total > MAX_TOTAL: raise ValueError("CoEvo sidecar read exceeds bound")
            digest = hashlib.sha256(native).hexdigest()
            expected = {"path": snapshot.relative_to(workspace).as_posix(), "sha256": digest, "bytes": len(native)}
            projection = project_history(native)
            if receipt.get("snapshot") != expected or receipt.get("accounting") != projection:
                raise ValueError("CoEvo snapshot changed or accounting mismatch")
            if receipt.get("native_generation") != projection["native_generation"]:
                raise ValueError("CoEvo generation mismatch")
            native_path = path.parent.parent / "history" / f"gen_{projection['native_generation']}.json"
            if receipt.get("native_path") != native_path.relative_to(workspace).as_posix():
                raise ValueError("CoEvo native path mismatch")
            sequences[path.parent] = sequence + 1
            value["saves"].append({"sequence": sequence, "artifact": snapshot.relative_to(output).as_posix(), **projection})
            value["artifacts"].extend([{"path": snapshot.relative_to(output).as_posix(), "sha256": digest},
                                       {"path": path.relative_to(output).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}])
        if paths:
            value["status"] = "recorded"
            value["warnings"].append("Native generation labels may repeat; sequence numbers identify distinct persistence events.")
        value["warnings"].append("Registered-history and usage counts do not establish physical evaluations or model requests.")
    except (ValueError, KeyError, TypeError, OSError, RecursionError):
        value["status"] = "partial"
        value["warnings"].append("CoEvo sidecar sequence is incomplete, changed, malformed or exceeded its observation bound.")
    return value
