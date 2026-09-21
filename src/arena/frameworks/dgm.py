"""Plan the pinned DGM CLI and read its native, unaudited JSON receipts.

No DGM code is imported here. The shared launcher supplies the isolated Git
workspace and dependency copies only when execution is explicitly requested.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat


COMMIT = "a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2"
_RUN_ID = re.compile(r"[0-9]{14}_[0-9]{6}")
_MEMBER_ID = re.compile(r"(?:initial|[0-9]{8}_[0-9]{6}_[0-9]{6})")
_MAX_RUNS = 8
_MAX_GENERATIONS = 80
_MAX_MEMBERS = 1024
_MAX_JSON = 4 * 1024 * 1024
_MAX_JOURNAL = 8 * 1024 * 1024
_MAX_TOTAL = 64 * 1024 * 1024


def _path(value, label, *, directory=False, exists=True):
    if not isinstance(value, (str, Path)) or not str(value) or "\x00" in str(value):
        raise ValueError(f"{label}: absolute path required")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{label}: absolute path required")
    if exists and not (path.is_dir() if directory else path.is_file()):
        raise ValueError(f"{label}: existing {'directory' if directory else 'file'} required")
    return path.absolute()


def _integer(request, key, default, maximum):
    value = request.get(key, default)
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{key}: integer in 1..{maximum} required")
    return value


def _boolean(request, key, default):
    value = request.get(key, default)
    if type(value) is not bool:
        raise ValueError(f"{key}: boolean required")
    return value


def _decoder():
    def constant(value):
        raise ValueError(f"Non-finite JSON constant: {value}")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    return json.JSONDecoder(parse_constant=constant, object_pairs_hook=pairs)


def _number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def _relative_repo(value):
    if type(value) is not str or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    return (not path.is_absolute() and ".." not in path.parts
            and len(path.parts) == 6
            and path.parts[:2] == ("polyglot", "polyglot-benchmark")
            and path.parts[3:5] == ("exercises", "practice")
            and all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in path.parts))


def _validate_polyglot_metadata(path, benchmark):
    if path.stat().st_size > _MAX_TOTAL:
        raise ValueError("polyglot_metadata exceeds 64 MiB")
    data = _decoder().decode(path.read_text(encoding="utf-8"))
    if type(data) is not list or not data or len(data) > 10000:
        raise ValueError("polyglot_metadata must be a nonempty native metadata array")
    for item in data:
        if type(item) is not dict or not _relative_repo(item.get("repo")):
            raise ValueError("Polyglot repo paths must be relative polyglot/polyglot-benchmark/<language>/exercises/practice/<task>")
        if not all(type(item.get(key)) is str and item[key] for key in
                   ("instance_id", "language", "problem_statement", "base_commit", "test_commit")):
            raise ValueError("Polyglot metadata is missing native task fields")
        repo = PurePosixPath(item["repo"])
        if (item["language"] != repo.parts[2]
                or item["instance_id"] != f"{repo.parts[2]}__{repo.name}"
                or any(not re.fullmatch(r"[a-fA-F0-9]{40}", item[key]) for key in ("base_commit", "test_commit"))
                or type(item.get("test_patch")) is not str):
            raise ValueError("Polyglot metadata must preserve prepared task identities, commits, and test patches")
        if not (benchmark.joinpath(*repo.parts[2:]) / ".git").is_dir():
            raise ValueError("Polyglot exercises must have their prepared local Git repositories")


class _Reader:
    """Read only bounded regular files beneath output, rejecting symlink paths."""

    def __init__(self, root):
        self.root = root
        self.consumed = 0
        self.artifacts = []

    def check_path(self, path):
        relative = path.relative_to(self.root)
        current = self.root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("Native artifact symlinks are not permitted")

    def read(self, path, limit):
        self.check_path(path)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise ValueError("Native artifact is not a bounded regular file")
            if self.consumed + before.st_size > _MAX_TOTAL:
                raise ValueError("Native result read exceeds 64 MiB total limit")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(raw) > limit or signature(before) != signature(after):
            raise ValueError("Native artifact changed while being read")
        self.check_path(path)
        if signature(path.stat(follow_symlinks=False)) != signature(after):
            raise ValueError("Native artifact was replaced while being read")
        self.consumed += len(raw)
        self.artifacts.append({"path": path.relative_to(self.root).as_posix(),
                               "sha256": hashlib.sha256(raw).hexdigest()})
        return raw.decode("utf-8")


def _generation_records(content):
    """Upstream writes pretty-printed JSON objects, despite the .jsonl suffix."""
    decoder = _decoder()
    records = []
    position = 0
    while position < len(content):
        while position < len(content) and content[position].isspace():
            position += 1
        if position == len(content):
            break
        if len(records) >= _MAX_GENERATIONS:
            return records, "Generation journal exceeds the 80-record reader limit."
        try:
            value, position = decoder.raw_decode(content, position)
        except (ValueError, RecursionError):
            return records, "Generation journal has an invalid or unfinished JSON record."
        if type(value) is not dict or type(value.get("generation")) is not int or value["generation"] < 0:
            return records, "Generation journal has an invalid generation record."
        if records and value["generation"] <= records[-1]["generation"]:
            return records, "Generation journal is not strictly increasing."
        row = {"generation": value["generation"]}
        for key in ("archive", "children", "children_compiled"):
            members = value.get(key)
            if (type(members) is not list or len(members) > _MAX_MEMBERS
                    or any(type(member) is not str or not _MEMBER_ID.fullmatch(member) for member in members)):
                return records, f"Generation journal has an invalid {key} list."
            row[key] = members
        records.append(row)
    return records, None


def _performance(value):
    if type(value) is not dict:
        return None
    score = _number(value.get("accuracy_score"))
    if score is None:
        return None
    result = {"accuracy_score": score, "validity": "unknown"}
    for key in ("total_resolved_instances", "total_submitted_instances"):
        count = value.get(key)
        if type(count) is int and count >= 0:
            result[key] = count
    return result


def _pilot_plan(reader):
    """Only a hash-consistent runtime plan can enable fresh-baseline labels."""
    try:
        plan = _decoder().decode(reader.read(reader.root / ".arena/plan.json", _MAX_JSON))
    except FileNotFoundError:
        return None
    if type(plan) is not dict or plan.get("command", {}).get("pilot_profile") != "gateway-polyglot-pilot":
        return None
    payload = {key: value for key, value in plan.items() if key != "sha256"}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    command = plan["command"]
    if (plan.get("schema") != "arena.native-plan/1" or plan.get("framework") != "dgm"
            or plan.get("source", {}).get("commit") != COMMIT or digest != plan.get("sha256")
            or not any(item.get("sha256") == command.get("preparation_sha256")
                       and Path(item.get("path", "")).name == "preparation.json" for item in plan.get("inputs", []))):
        raise ValueError("DGM gateway plan provenance is inconsistent")
    return command


def _fresh_baseline(reader, initial, plan):
    from .drivers.dgm_pilot import TASKS, baseline_complete
    proof_path = reader.root / "workspace/dgm/.arena-pilot/baseline-proof.json"
    proof = _decoder().decode(reader.read(proof_path, _MAX_JSON))
    if (type(proof) is not dict or proof.get("schema") != "arena.dgm-fresh-baseline/1"
            or proof.get("profile") != plan["pilot_profile"] or proof.get("model") != plan["model"]
            or proof.get("task_ids") != list(TASKS) or proof.get("source_commit") != COMMIT
            or proof.get("preparation_sha256") != plan["preparation_sha256"]
            or proof.get("native_baseline_completed") is not True or proof.get("canonical_evaluation") is not False
            or type(proof.get("files")) is not dict or not 1 <= len(proof["files"]) <= 4096):
        raise ValueError("DGM fresh-baseline proof does not match this run")
    content = {}
    for name, expected in proof["files"].items():
        relative = PurePosixPath(name)
        if (relative.is_absolute() or ".." in relative.parts or str(relative) != name or "\\" in name
                or not re.fullmatch(r"[a-f0-9]{64}", expected)):
            raise ValueError("DGM fresh-baseline proof contains an invalid artifact path/hash")
        value = reader.read(initial / name, _MAX_JOURNAL)
        if hashlib.sha256(value.encode()).hexdigest() != expected:
            raise ValueError("DGM fresh-baseline artifact hash mismatch")
        if name.endswith(".json"):
            content[name] = _decoder().decode(value)
    report_name = plan["model"] + "_0.0.json"
    if proof.get("report") != report_name or report_name not in content or "metadata.json" not in content:
        raise ValueError("DGM fresh-baseline proof lacks the actual report and metadata")
    baseline_complete(content[report_name], initial / "predictions" / (plan["model"] + "_0"))
    performance = content["metadata.json"].get("overall_performance")
    if (content["metadata.json"].get("run_id") != "initial" or type(performance) is not dict or performance != proof.get("native_performance")
            or performance.get("total_submitted_instances") != 2
            or performance.get("total_resolved_instances") != content[report_name]["resolved_instances"]
            or performance.get("accuracy_score") != content[report_name]["resolved_instances"] / 2):
        raise ValueError("DGM fresh baseline does not retain native report totals")
    return {"model": plan["model"], "task_ids": list(TASKS), "cached_initial": False,
            "provenance": "fresh_native_two_task", "canonical_evaluation": False,
            "overall_performance": _performance(performance)}


class DGMAdapter:
    id = "dgm"
    commit = COMMIT

    def prepare(self, source_dir: Path, request: dict, output_dir: Path) -> dict:
        if type(request) is dict and "profile" in request:
            return self._prepare_gateway(source_dir, request, output_dir)
        allowed = {"python", "benchmark", "max_generation", "selfimprove_size", "selfimprove_workers",
                   "num_swe_evals", "choose_selfimproves_method", "update_archive", "shallow_eval",
                   "no_full_eval", "eval_noise", "run_baseline", "swe_bench_dir",
                   "polyglot_metadata", "polyglot_benchmark_dir"}
        if type(request) is not dict or set(request) - allowed:
            raise ValueError("Unknown DGM request option; credentials belong in the environment")
        source = _path(source_dir, "source_dir", directory=True)
        if not (source / "DGM_outer.py").is_file():
            raise ValueError("Pinned DGM_outer.py entrypoint is missing")
        python = _path(request.get("python"), "python")
        if not os.access(python, os.X_OK):
            raise ValueError("python: executable file required")
        output = _path(output_dir, "output_dir", directory=True, exists=False)
        if output.exists() and not output.is_dir():
            raise ValueError("output_dir must be a directory")
        if any(character.isspace() for character in str(output)):
            raise ValueError("DGM output paths cannot contain whitespace: native commands split absolute paths")
        workspace = output / "workspace" / "dgm"
        if workspace.exists() or workspace.is_symlink():
            raise ValueError("DGM requires a new isolated workspace")
        benchmark = request.get("benchmark")
        if benchmark not in ("swe-bench", "polyglot"):
            raise ValueError("benchmark must be swe-bench or polyglot; arbitrary Arena tasks are not supported")
        staging = []
        if benchmark == "swe-bench":
            if "polyglot_metadata" in request or "polyglot_benchmark_dir" in request:
                raise ValueError("Polyglot inputs cannot be used in a SWE-bench run")
            dependency = _path(request.get("swe_bench_dir"), "swe_bench_dir", directory=True)
            if not (dependency / "swebench/harness/run_evaluation.py").is_file():
                raise ValueError("swe_bench_dir must contain the prepared SWE-bench evaluator checkout")
            staging.append({"source": str(dependency), "destination": "swe_bench/SWE-bench"})
        else:
            if "swe_bench_dir" in request:
                raise ValueError("swe_bench_dir cannot be used in a Polyglot run")
            metadata = _path(request.get("polyglot_metadata"), "polyglot_metadata")
            dependency = _path(request.get("polyglot_benchmark_dir"), "polyglot_benchmark_dir", directory=True)
            _validate_polyglot_metadata(metadata, dependency)
            staging.extend([{"source": str(metadata), "destination": "polyglot/polyglot_benchmark_metadata.json"},
                            {"source": str(dependency), "destination": "polyglot/polyglot-benchmark"}])
        generations = _integer(request, "max_generation", None, 80)
        size = _integer(request, "selfimprove_size", 1, 8)
        workers = _integer(request, "selfimprove_workers", 1, 8)
        evaluations = _integer(request, "num_swe_evals", 1, 5)
        if workers > size:
            raise ValueError("selfimprove_workers cannot exceed selfimprove_size")
        selection = request.get("choose_selfimproves_method", "score_child_prop")
        if selection not in ("random", "score_prop", "score_child_prop"):
            raise ValueError("Pinned DGM supports random/score_prop or its default score_child_prop; best has an upstream CLI bug")
        archive = request.get("update_archive", "keep_all")
        if archive not in ("keep_all", "keep_better"):
            raise ValueError("update_archive must be keep_all or keep_better")
        noise = request.get("eval_noise", 0.1)
        if _number(noise) is None or not 0 <= noise <= 1:
            raise ValueError("eval_noise must be a finite number in 0..1")
        argv = [str(python), "DGM_outer.py", "--max_generation", str(generations),
                "--selfimprove_size", str(size), "--selfimprove_workers", str(workers),
                "--num_swe_evals", str(evaluations), "--update_archive", archive,
                "--eval_noise", str(noise)]
        if selection != "score_child_prop":
            argv += ["--choose_selfimproves_method", selection]
        for key in ("shallow_eval", "no_full_eval"):
            if _boolean(request, key, True):
                argv.append(f"--{key}")
        if benchmark == "polyglot":
            argv.append("--polyglot")
        if "run_baseline" in request:
            baseline = request["run_baseline"]
            if baseline not in ("no_selfimprove", "no_darwin"):
                raise ValueError("run_baseline must be no_selfimprove or no_darwin")
            argv += ["--run_baseline", baseline]
        return {"argv": argv, "cwd": str(workspace),
                "env": {"PATH": str(python.parent) + os.pathsep + os.environ.get("PATH", "")},
                "workspace_copy": True, "workspace_inputs": staging,
                "input_paths": [item["source"] for item in staging],
                "evaluator_profile": f"dgm-native-{benchmark}",
                "expected_artifacts": ["workspace/dgm/output_dgm/*/dgm_metadata.jsonl",
                                       "workspace/dgm/output_dgm/*/*/metadata.json"]}

    def _prepare_gateway(self, source_dir, request, output_dir):
        from .drivers import dgm_pilot as pilot
        allowed = {"python", "benchmark", "profile", "model", "preparation_dir", "dependency_freeze"}
        if (set(request) != allowed or request["profile"] != pilot.PROFILE
                or request["benchmark"] != "polyglot" or request["model"] not in pilot.MODELS):
            raise ValueError("DGM gateway pilot requires its fixed two-task profile and an exact reviewed model")
        source = _path(source_dir, "source_dir", directory=True)
        prepared = _path(request["preparation_dir"], "preparation_dir", directory=True)
        freeze = _path(request["dependency_freeze"], "dependency_freeze")
        if (source / ".env").exists() or (source / ".env").is_symlink():
            raise ValueError("DGM pilot credentials must come only from the worker environment")
        pilot.validate_preparation(source, prepared, freeze)
        native = prepared / "native-inputs/polyglot"
        plan = self.prepare(source, {"python": request["python"], "benchmark": "polyglot", "max_generation": 1,
            "polyglot_metadata": str(native / "polyglot_benchmark_metadata.json"),
            "polyglot_benchmark_dir": str(native / "polyglot-benchmark")}, output_dir)
        staging = [(prepared / "preparation.json", "preparation.json"),
                   (prepared / "native-inputs", "native-inputs"),
                   (prepared / "provider-overlays", "provider-overlays"),
                   (prepared / "native-image-recipes.json", "native-image-recipes.json"),
                   (freeze, "dependencies.txt")]
        workspace = Path(plan["cwd"])
        plan["argv"] = [request["python"], "-m", "arena.frameworks.drivers.dgm_pilot", "--model", request["model"]]
        plan["workspace_inputs"] = [{"source": str(path), "destination": ".arena-pilot/" + name} for path, name in staging]
        plan["input_paths"] = [str(path) for path, _ in staging] + [str(Path(pilot.__file__)), str(Path(pilot.__file__).with_name("dgm_gateway.py"))]
        plan["env"].update(PYTHONPATH=os.pathsep.join((str(workspace), str(Path(__file__).resolve().parents[2]))),
            DOCKER_HOST=pilot.DOCKER_HOST, ARENA_DGM_MODEL=request["model"], ARENA_DGM_GATEWAY_URL=pilot.GATEWAY,
            OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
        plan["pilot_profile"] = pilot.PROFILE
        plan["model"] = request["model"]
        plan["preparation_sha256"] = pilot.sha(prepared / "preparation.json")
        plan["source_evidence"] = {name: pilot.sha(source / name) for name in
            (*pilot.SOURCE_HASHES, "DGM_outer.py", "polyglot/harness.py", "utils/evo_utils.py")}
        plan["expected_artifacts"] += ["workspace/dgm/.arena-pilot/baseline-proof.json",
                                       "workspace/dgm/initial_polyglot/*.json"]
        return plan

    def read_results(self, output_dir: Path) -> dict:
        root = _path(output_dir, "output_dir", directory=True).resolve()
        reader = _Reader(root)
        result = {"schema": "arena.native-result/1", "framework": self.id,
                  "canonical_evaluation": False, "status": "missing", "native": {"runs": []},
                  "artifacts": reader.artifacts,
                  "warnings": ["DGM native accuracy is unaudited; evaluation validity is unknown. Cached initial results are not a fresh Arena evaluation."]}
        pilot_plan = _pilot_plan(reader)
        if pilot_plan:
            result["warnings"] = ["DGM native accuracy is unaudited; evaluation validity is unknown. Fresh-baseline labels require matching run-local proof and native reports."]
            result["native"]["profile"] = pilot_plan["pilot_profile"]
        runs_dir = root / "workspace/dgm/output_dgm"
        reader.check_path(runs_dir)
        if not runs_dir.exists():
            result["warnings"].append("Native output_dgm directory is missing; no score is inferred.")
            return result
        if not runs_dir.is_dir():
            raise ValueError("Native output_dgm must be a directory")
        paths = []
        with os.scandir(runs_dir) as entries:
            for index, entry in enumerate(entries):
                if index >= 4096:
                    raise ValueError("Native output directory exceeds the 4096-entry scan limit")
                if not _RUN_ID.fullmatch(entry.name):
                    continue
                if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                    raise ValueError("Native run path must be a directory, not a symlink")
                paths.append(Path(entry.path))
                if len(paths) > _MAX_RUNS:
                    raise ValueError("Native output has more than eight run directories")
        partial = False
        for run in sorted(paths):
            journal = run / "dgm_metadata.jsonl"
            try:
                content = reader.read(journal, _MAX_JOURNAL)
            except FileNotFoundError:
                partial = True
                result["warnings"].append(f"{run.name}: generation journal is missing.")
                continue
            records, issue = _generation_records(content)
            if issue:
                partial = True
                result["warnings"].append(f"{run.name}: {issue}")
            row = {"run_id": run.name, "generations": records, "members": []}
            members = {member for record in records for key in ("archive", "children") for member in record[key]}
            if len(members) > _MAX_MEMBERS:
                raise ValueError("Native archive exceeds the 1024-member reader limit")
            if not records:
                partial = True
            for member in sorted(members):
                path = run / member / "metadata.json"
                try:
                    metadata = _decoder().decode(reader.read(path, _MAX_JSON))
                except FileNotFoundError:
                    partial = True
                    result["warnings"].append(f"{run.name}/{member}: native metadata is missing.")
                    continue
                except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
                    partial = True
                    result["warnings"].append(f"{run.name}/{member}: native metadata is invalid JSON.")
                    continue
                if type(metadata) is not dict or metadata.get("run_id") != member:
                    partial = True
                    result["warnings"].append(f"{run.name}/{member}: metadata identity is inconsistent.")
                    continue
                record = {"run_id": member, "cached_initial": member == "initial",
                          "validity": "unknown", "overall_performance": _performance(metadata.get("overall_performance"))}
                if member == "initial" and pilot_plan:
                    record["cached_initial"] = None
                    try:
                        verified = _fresh_baseline(reader, run / member, pilot_plan)
                    except (FileNotFoundError, ValueError, UnicodeDecodeError, RecursionError, TypeError):
                        partial = True
                        record["baseline_provenance"] = "unverified"
                        result["warnings"].append(f"{run.name}/initial: fresh-baseline proof is missing or inconsistent.")
                    else:
                        record["cached_initial"] = False
                        record["baseline_provenance"] = verified["provenance"]
                        result["native"]["fresh_baseline"] = verified
                parent = metadata.get("parent_commit")
                if type(parent) is str and _MEMBER_ID.fullmatch(parent):
                    record["parent_commit"] = parent
                deep = _performance(metadata.get("overall_performance_deep"))
                if deep is not None:
                    record["overall_performance_deep"] = deep
                row["members"].append(record)
            result["native"]["runs"].append(row)
        if paths:
            result["status"] = "partial" if partial else "recorded"
        else:
            result["warnings"].append("No native timestamped DGM run was found; no score is inferred.")
        return result


adapter = DGMAdapter()
