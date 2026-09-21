"""Inert native-shaped persistence fixtures; no CoEvo import or evaluation."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from arena.frameworks.drivers import coevo_history as history
from arena.frameworks.drivers import coevo_observed_gateway as driver
from arena.frameworks.recipes import load_recipes, validate_recipe


EVIDENCE = {"repository_commit": history.COMMIT, "repository_files": history.SOURCE_HASHES,
            "evotoolkit_version": "1.0.2", "dependency_files": history.DEPENDENCY_HASHES}


def rows():
    result = []
    for chain in range(4):
        row = {"sol_string": "" if chain < 2 else f"def equation(x,v,p): return p[{chain}] * x",
               "metadata": {"chain_id": chain, **({"parse_error": "Failed after retries"} if chain < 2 else {"Ideas": [], "raw_content": "inert response"})},
               "evaluation_res": {"valid": chain >= 2, "score": float("-inf") if chain < 2 else -0.01 * chain,
                                  "additional_info": {"error": "parse failure"} if chain < 2 else {"mse": .01 * chain}}}
        result.extend([row, row])  # the same native representative is registered twice
    return result


class NativeStore:
    """Matches RunStore's real write mode/filename and payload shape."""
    def __init__(self, output):
        self.output_path = str(output)
        self.history_dir = str(output / "history")
        Path(self.history_dir).mkdir(parents=True)
        self.calls = []

    def save_generation_history(self, generation, solutions, usage, statistics=None):
        self.calls.append((generation, solutions, usage, statistics))
        value = {"generation": generation, "solutions": solutions, "usage": usage, "statistics": statistics or {}}
        Path(self.history_dir, f"gen_{generation}.json").write_text(json.dumps(value, indent=2, allow_nan=True))
        return "native-return-value"


def test_duplicate_rows_never_become_physical_evaluation_or_model_counts():
    payload = {"generation": 0, "solutions": rows(), "usage": [{}, {"input_tokens": 1}] * 4, "statistics": {"total_solutions": 8}}
    raw = json.dumps(payload, allow_nan=True).encode()
    result = history.project_history(raw)
    assert result["native_history_rows"] == 8 and result["distinct_registered_records"] == 4
    assert result["duplicate_registered_rows"] == 4
    assert result["native_usage_records"] == 8 and result["nonempty_native_usage_records"] == 4
    assert result["task_evaluation_calls"] is None and result["physical_model_requests"] is None
    assert [g["row_indices"] for g in result["record_groups"]] == [[0, 1], [2, 3], [4, 5], [6, 7]]
    assert "-Infinity" in raw.decode()  # preserved native invalid score, not a finite metric
    json.dumps(result, allow_nan=False)


def test_native_two_save_overwrite_is_preserved_but_both_exact_snapshots_survive(tmp_path):
    output = tmp_path.resolve() / "run"
    workspace = output / "workspace/coevo-observed-v2"
    store = NativeStore(workspace / "results/oscillation_1_coevo")
    original = NativeStore.save_generation_history
    initial = rows(); offspring = deepcopy(initial[:2]); offspring[0]["metadata"]["chain_id"] = 4
    usage = [{}, {"input_tokens": 1}] * 4; stats = {"total_solutions": 8}
    with history.capture_saves(NativeStore, workspace, EVIDENCE):
        assert store.save_generation_history(0, initial, usage, stats) == "native-return-value"
        first = Path(store.history_dir, "gen_0.json").read_bytes()
        assert store.save_generation_history(0, offspring, [{}], {"total_solutions": 2}) == "native-return-value"
        second = Path(store.history_dir, "gen_0.json").read_bytes()
    assert NativeStore.save_generation_history is original
    assert first != second
    side = Path(store.output_path) / "arena-history"
    assert (side / "save_000000.native.json").read_bytes() == first
    assert (side / "save_000001.native.json").read_bytes() == second
    assert Path(store.history_dir, "gen_0.json").read_bytes() == second
    assert store.calls[0][1] is initial and store.calls[0][2] is usage and store.calls[0][3] is stats
    assert len(store.calls) == 2 and len(initial) == 8 and initial[0] is initial[1]
    receipts = [json.loads((side / f"save_{i:06d}.receipt.json").read_text()) for i in range(2)]
    assert [r["sequence"] for r in receipts] == [0, 1]
    assert [r["native_generation"] for r in receipts] == [0, 0]
    assert all(r["native_state_modified"] is False and r["source"] == EVIDENCE for r in receipts)
    projection = history.read_sidecars(output)
    assert projection["status"] == "recorded" and len(projection["saves"]) == 2
    assert all(not Path(a["path"]).is_absolute() and a["path"].startswith("workspace/coevo-observed-v2/") for a in projection["artifacts"])
    (side / "save_000000.native.json").write_bytes(b"{}")
    assert history.read_sidecars(output)["status"] == "partial"


def test_native_failure_remains_failure_without_a_success_sidecar(tmp_path):
    class BrokenStore(NativeStore):
        def save_generation_history(self, *args): raise RuntimeError("native persistence failed")
    store = BrokenStore(tmp_path.resolve() / "results/task")
    original = BrokenStore.save_generation_history
    with pytest.raises(RuntimeError, match="native persistence"):
        with history.capture_saves(BrokenStore, tmp_path.resolve(), EVIDENCE):
            store.save_generation_history(0, rows(), [])
    assert BrokenStore.save_generation_history is original
    assert not (Path(store.output_path) / "arena-history").exists()


def test_sidecar_never_overwrites_prior_sequences_or_reads_pickles(tmp_path):
    workspace = tmp_path.resolve()
    store = NativeStore(workspace / "results/task")
    (Path(store.output_path) / "checkpoint").mkdir()
    (Path(store.output_path) / "checkpoint/state.pkl").write_bytes(b"not a pickle; never read")
    with history.capture_saves(NativeStore, workspace, EVIDENCE): store.save_generation_history(0, rows(), [])
    saved = Path(store.output_path) / "arena-history/save_000000.native.json"
    before = saved.read_bytes()
    with pytest.raises(FileExistsError):
        with history.capture_saves(NativeStore, workspace, EVIDENCE): store.save_generation_history(0, rows()[:2], [])
    assert saved.read_bytes() == before


def test_reader_rejects_missing_sequence_symlinks_and_forged_provenance(tmp_path):
    output = tmp_path.resolve()
    workspace = output / "workspace/coevo-observed-v2"
    store = NativeStore(workspace / "results/oscillation_1_coevo")
    with history.capture_saves(NativeStore, workspace, EVIDENCE): store.save_generation_history(0, rows(), [])
    side = Path(store.output_path) / "arena-history"
    receipt = side / "save_000000.receipt.json"
    original = receipt.read_bytes()
    tampered = json.loads(original); tampered["source"]["repository_commit"] = "0" * 40
    receipt.write_text(json.dumps(tampered))
    assert history.read_sidecars(output)["status"] == "partial"
    receipt.write_bytes(original)
    source = side / "save_000000.native.json"; raw = source.read_bytes(); source.unlink()
    outside = output / "outside"; outside.write_bytes(raw); source.symlink_to(outside)
    assert history.read_sidecars(output)["status"] == "partial"
    source.unlink(); source.write_bytes(raw)
    receipt.unlink()
    assert history.read_sidecars(output)["status"] == "partial"  # interrupted receipt write remains visible


def test_source_guards_reject_unreviewed_native_and_dependency_files(tmp_path, monkeypatch):
    source, dependency = tmp_path.resolve() / "source", tmp_path.resolve() / "dependency"
    hashes = {}
    for root, expected in ((source, history.SOURCE_HASHES), (dependency, history.DEPENDENCY_HASHES)):
        local = {}
        for name in expected:
            file = root / name; file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"# inert source fixture")
            local[name] = hashlib.sha256(file.read_bytes()).hexdigest()
        hashes[root] = local
    monkeypatch.setattr(history, "SOURCE_HASHES", hashes[source]); monkeypatch.setattr(history, "DEPENDENCY_HASHES", hashes[dependency])
    os.link(dependency / "core/store.py", tmp_path / "uv-cache-link.py")
    assert history.verify_sources(source, dependency)["repository_commit"] == history.COMMIT
    (dependency / "core/store.py").write_bytes(b"changed")
    with pytest.raises(ValueError, match="source hash changed"): history.verify_sources(source, dependency)


def test_v2_driver_adds_observation_only_at_native_entry_after_existing_setup(monkeypatch):
    events = []
    native = SimpleNamespace(run_path=lambda path, **kw: events.append(("native", path)), run_module=lambda *a: None)
    monkeypatch.setattr(driver.cpu_program_gateway, "runpy", native)
    def existing_main(args):
        events.append(("existing-setup", args))
        driver.cpu_program_gateway.runpy.run_path("main_run.py", run_name="__main__")
    monkeypatch.setattr(driver.cpu_program_gateway, "main", existing_main)
    @contextmanager
    def observer(path):
        events.append(("observe", path)); yield; events.append(("restore", path))
    monkeypatch.setattr(driver, "observe_native_saves", observer)
    driver.main(["--model", "gpt-5.6-sol"])
    assert [e[0] for e in events] == ["existing-setup", "observe", "native", "restore"]
    assert events[0][1] == ["--engine", "coevo", "--model", "gpt-5.6-sol"]
    assert driver.cpu_program_gateway.runpy is native
    with pytest.raises(ValueError): driver.main(["--engine=codeevolve"])


def test_versioned_recipe_keeps_old_identity_and_seven_model_plans_distinct(tmp_path):
    recipes = load_recipes(); old, new = recipes["coevo"], recipes["coevo-observed-v2"]
    validate_recipe(new)
    assert new["participant_ids"] == ["coevo"] and new["repository"] == old["repository"]
    assert all(p["invocation"]["target"] != "arena.frameworks.drivers.coevo_observed_gateway" for p in old["profiles"])
    script = Path(__file__).resolve().parents[2] / "scripts/deployment/prepare_coevo_observed_v2.py"
    spec = importlib.util.spec_from_file_location("prepare_coevo_observed_v2_test", script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    items = module.templates(tmp_path, tmp_path / "configs", new)
    assert len(items) == 7 and len({x["id"] for x in items}) == 7
    for item in items:
        assert item["framework"] == item["spec"]["framework"] == "coevo-observed-v2"
        assert item["spec"]["source_dir"] == str(tmp_path / "sources/coevo")
        request = item["spec"]["request"]
        assert request["arguments"][request["arguments"].index("--model") + 1] == item["model"]
        assert request["arguments"][request["arguments"].index("--max_gen") + 1] == "1"
