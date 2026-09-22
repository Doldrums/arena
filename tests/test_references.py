"""Scientific evidence semantics, using only the shipped offline snapshot."""
from copy import deepcopy
import json
import hashlib
import importlib.util
import math
from pathlib import Path
import subprocess
import sys

import pytest

from arena.references import get_references, summarize, validate_references
from arena.registry import RegistryError, get_catalog


@pytest.fixture(scope="module")
def catalog():
    return get_catalog()


@pytest.fixture(scope="module")
def snapshot():
    return get_references()


def task(snapshot, task_id):
    return next(row for row in snapshot["tasks"] if row["task_id"] == task_id)


def anchor(snapshot, task_id, kind="published_reference"):
    return next(row for row in task(snapshot, task_id)["anchors"] if row["kind"] == kind)


def test_full_coverage_and_honest_evidence_counts(snapshot, catalog):
    assert {row["task_id"] for row in snapshot["tasks"]} == {row["id"] for row in catalog["tasks"]}
    summary = snapshot["summary"]
    assert summary["task_count"] == 959
    assert summary["tasks_with_published_reference"] == 75
    assert summary["tasks_with_recorded_baseline"] == 654
    assert summary["valid_recorded_baselines"] == 577
    assert summary["validity_unknown_baselines"] == 77
    assert summary["tasks_without_numeric_reference"] == 305
    assert summary["tasks_with_recorded_reproduction"] == 34
    assert summary["arena_reproduced_references"] == 0
    assert summary["current_sota_status"] == "not_assessed"


def test_adapted_validity_contracts_do_not_inherit_original_protocol_baselines(snapshot):
    adapted = ["sciel-math-" + suffix for suffix in (
        "difference-bases", "finite-field-nikodym", "turan-hypergraph",
        "equidistant-points-convex", "erdos-discrepancy", "no-5-on-a-sphere",
        "erdos-squarefree", "factoring-factorials", "furstenberg-sarkozy",
        "subsets-grid-no-isosceles", "flat-polynomials", "sendov-conjecture")]
    for task_id in [*adapted, "sciel-bench-k-module-problem"]:
        row = task(snapshot, task_id)
        assert not any(anchor["kind"] == "recorded_seed_baseline" for anchor in row["anchors"])
        assert any("different task family, protocol or direction" in note
                   for note in row["evaluation"]["notes"])


def test_missing_is_empty_not_zero_and_zero_is_a_real_score(snapshot):
    missing = [row for row in snapshot["tasks"] if row["status"] == "missing"]
    assert missing and all(row["anchors"] == [] for row in missing)
    zeros = [a for row in snapshot["tasks"] for a in row["anchors"] if a["value"] == 0]
    assert zeros and all(a["kind"] == "recorded_seed_baseline" for a in zeros)
    assert all(a["source"]["path"] in {"validation/suite-report.json", "validation/science-expansion-report.json"} for a in zeros)


def test_complex_tensor_rank_and_raw_minimization(snapshot):
    row = task(snapshot, "alphaevolve-matrix-multiplication-4-4-4")
    assert row["evaluation"]["parameters"]["coefficient_domain"] == "gaussian_half_integers"
    published = anchor(snapshot, row["task_id"])
    baseline = anchor(snapshot, row["task_id"], "recorded_seed_baseline")
    assert (published["value"], published["direction"]) == (48, "minimize")
    assert baseline["value"] == 64
    assert baseline["reported_combined_score"] == -64
    assert published["reproduction"] == "recorded_upstream"
    assert published["reproduction_source"]["path"] == "validation/tensor-exact.json"


def test_geometry_metric_transforms_are_explicit(snapshot):
    distance = anchor(snapshot, "alphaevolve-maximum-to-minimum-distance-ratio-n-14-d-3")
    assert "Squared" in distance["metric_label"]
    assert distance["value"] == 4.1658497672256525
    triangle = next(a for row in snapshot["tasks"] for a in row["anchors"]
                    if a["kind"] == "published_reference" and "enclosing equilateral" in a["metric_label"])
    assert " / " in triangle["metric_label"]
    circle = anchor(snapshot, "alphaevolve-circle-packing-in-unit-square")
    assert circle["value"] == 2.6358627564136983
    assert any("strict" in note for note in circle["notes"])


def test_notebook_variants_are_not_merged(snapshot):
    third = anchor(snapshot, "alphaevolve-third-autocorrelation-inequality")
    absolute = anchor(snapshot, "alphaevolve-signed-autocorrelation-maximum-absolute-value-variant")
    assert third["value"] == 1.4556427953745406
    assert absolute["value"] == 1.4687620697410226
    assert third["metric_label"] != absolute["metric_label"]


def test_llm_historical_smoke_and_configured_default_are_distinct(snapshot):
    row = task(snapshot, "promptbreeder-gsm8k")
    baseline = anchor(snapshot, row["task_id"], "recorded_seed_baseline")
    assert row["evaluation"]["case_count"] == 10
    assert row["evaluation"]["case_count_kind"] == "configured_default"
    assert baseline["evaluation"]["case_count"] == 5
    assert baseline["evaluation"]["case_count_kind"] == "historical_smoke"
    assert baseline["value"] == 1.0
    assert baseline["comparison"] == "historical_smoke_only"
    assert any("full named benchmark" in note for note in baseline["notes"])
    assert all(a["kind"] != "published_reference" for a in row["anchors"])


def test_regression_split_denominator_and_ode_score(snapshot):
    row = task(snapshot, "coevo-oscillation-1")
    assert row["evaluation"]["case_count"] == 10000
    assert set(row["evaluation"]["splits"]) == {"train", "test_id", "test_ood"}
    assert all(split["source"]["sha256"] for split in row["evaluation"]["splits"].values())
    baseline = anchor(snapshot, row["task_id"], "recorded_seed_baseline")
    assert baseline["metric_label"] == "NMSE on the in-distribution test split"
    assert baseline["value"] == 0.09591592602181821
    ode = anchor(snapshot, "dga2d-ode-solver-van-der-pol", "recorded_seed_baseline")
    assert "function evaluations" in ode["metric_label"]


def test_wrapper_score_is_not_presented_as_paper_cost(snapshot):
    baseline = anchor(snapshot, "coral-cloudcast", "recorded_seed_baseline")
    assert "Wrapper fitness" in baseline["metric_label"]
    assert baseline["score_space"] == "reported_score_or_selected_fitness"
    assert baseline["automatic_comparison"] is False
    assert baseline["direction"] == "maximize"


@pytest.mark.parametrize("mutation", [
    lambda d: d["catalog_binding"].update(manifest_sha256="0" * 64),
    lambda d: d["catalog_binding"].update(catalog_sha256="0" * 64),
    lambda d: d["tasks"].pop(),
    lambda d: d["tasks"].append(deepcopy(d["tasks"][0])),
    lambda d: d["summary"].update(valid_recorded_baselines=697),
    lambda d: d["tasks"][0].update(direction="maximize"),
])
def test_tampered_coverage_or_binding_rejected(snapshot, catalog, mutation):
    data = deepcopy(snapshot)
    mutation(data)
    with pytest.raises(RegistryError):
        validate_references(data, catalog)


@pytest.mark.parametrize("field,value", [
    ("value", float("nan")), ("value", True), ("metric", "combined_score"),
    ("direction", "minimize"), ("current_sota", "verified_current_sota"),
    ("automatic_comparison", True), ("reproduction", "arena_reproduced"),
    ("validity", False),
])
def test_unsupported_claims_and_metric_mismatch_rejected(snapshot, catalog, field, value):
    data = deepcopy(snapshot)
    item = anchor(data, "alphaevolve-circle-packing-in-unit-square")
    item[field] = value
    with pytest.raises(RegistryError):
        validate_references(data, catalog)


def test_isolated_snapshot_return_and_offline_cli(snapshot):
    data = get_references()
    data["tasks"].clear()
    assert len(get_references()["tasks"]) == 959
    result = subprocess.run([sys.executable, "-m", "arena.references", "validate"],
                            text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == snapshot["summary"]


def test_no_local_workstation_paths_or_unpinned_source_links(snapshot):
    raw = json.dumps(snapshot)
    assert not any(path in raw for path in ("/Users/", "/home/", "/tmp/", "OPENROUTER_API_KEY="))
    from arena.task_sources import source_url
    binding = snapshot["catalog_binding"]
    for row in snapshot["tasks"]:
        for item in row["anchors"]:
            assert item["source"]["url"] == source_url(binding, item["source"]["path"])
            assert len(item["source"]["sha256"]) == 64


def test_new_science_receipts_are_bound_to_current_code_and_not_arena_results(snapshot):
    science = [(row, item) for row in snapshot["tasks"] for item in row["anchors"]
               if item["source"]["path"] == "validation/science-expansion-report.json"]
    assert len(science) == 45
    for row, item in science:
        if item.get("code_verification") == "historical_code_changed":
            assert "execution_identity" not in item
            assert item["historical_code"]["changed_paths"]
            assert item["historical_code"]["import_source"]["path"] == "import-receipt.json"
        else:
            identity = item["execution_identity"]
            assert identity["source_execution"] is True and identity["fixture_only"] is False
            assert identity["evaluator_source"] == row["evaluation"]["evaluator_source"]
            assert identity["candidate_sha256"] == identity["candidate_source"]["sha256"]
        assert item["validity"] is True
        assert item["reproduction"] == "not_recorded"
        assert item["automatic_comparison"] is False
    # The same old ID now denotes a changed tracking protocol: its previous
    # successful suite score must not survive the newer blocked receipt.
    blocked = task(snapshot, "science-particle-helical-track-reconstruction")
    assert blocked["anchors"] == []
    assert any("older suite score is not carried forward" in text for text in blocked["evaluation"]["notes"])
    replaced = anchor(snapshot, "science-particle-collider-anomaly-ranking", "recorded_seed_baseline")
    assert replaced["source"]["path"] == "validation/science-expansion-report.json"


def test_lennard_jones_reference_preserves_signed_energy_and_putative_scope(snapshot):
    item = anchor(snapshot, "science-chemistry-lennard-jones-38")
    assert item["value"] == -173.928427 and item["direction"] == "minimize"
    assert "Lennard-Jones energy" in item["metric_label"]
    assert any("not a proven optimum" in note for note in item["notes"])
    assert item["reproduction"] == "not_recorded"


@pytest.mark.parametrize("mutation", [
    lambda a: a["source"].update(path="validation/unknown-report.json"),
    lambda a: a["execution_identity"].update(evaluator_sha256="0" * 64),
    lambda a: a["execution_identity"]["candidate_source"].update(path="suite/another/initial_program.py"),
    lambda a: a["execution_identity"].update(fixture_only=True),
    lambda a: a.update(execution_identity=None),
    lambda a: a.pop("execution_identity"),
    lambda a: a.update(validity=None),
])
def test_science_reader_rejects_unbound_or_fixture_receipts(source_fixture, mutation):
    builder, source, catalog, *_ = source_fixture
    data = builder.build(source, catalog)
    item = anchor(data, "science-new", "recorded_seed_baseline")
    mutation(item)
    with pytest.raises(RegistryError):
        validate_references(data, catalog)


@pytest.fixture
def source_fixture(tmp_path):
    """A tiny real Git history; source programs fail if anyone executes them."""
    spec = importlib.util.spec_from_file_location("reference_builder", Path(__file__).parents[1] / "scripts/build_references.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    source = tmp_path / "source"
    source.mkdir()

    def write(path, value):
        target = source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value) if not isinstance(value, str) else value)

    def digest(path):
        return hashlib.sha256((source / path).read_bytes()).hexdigest()

    definitions = [
        ("reference-sat", "sat_solver"), ("science-new", "science_example"),
        ("science-blocked", "science_example"), ("absent", "science_example"),
        ("changed", "science_example"),
    ]
    tasks, suite_rows = [], []
    for task_id, family in definitions:
        problem = {"protocol": "recreated", "family": family, "direction": "minimize", "parameters": {}}
        problem_path = f"suite/{task_id}/problem.json"
        write(problem_path, problem)
        write(f"suite/{task_id}/evaluator.py", "raise AssertionError('upstream evaluator must never execute')\n")
        write(f"suite/{task_id}/initial_program.py", "raise AssertionError('upstream candidate must never execute')\n")
        tasks.append({"id": task_id, **{k: problem[k] for k in ("protocol", "family", "direction")},
                      "metric": "score", "contract_source": {"sha256": digest(problem_path)}})
        if task_id not in {"absent", "science-new"}:
            suite_rows.append({"id": task_id, "family": "old_family" if task_id == "changed" else family,
                               "protocol": "recreated", "direction": "minimize", "status": "ok",
                               "score": 7.0, "valid": True})
    candidate_path = "suite/science-new/initial_program.py"
    evaluator_path = "suite/science-new/evaluator.py"
    science_row = {"id": "science-new", "status": "ok", "protocol": "recreated", "score": 2.0,
                   "valid": True, "source_execution": True, "fixture_only": False,
                   "candidate_sha256": digest(candidate_path), "evaluator_sha256": digest(evaluator_path),
                   "file_sha256": {candidate_path: digest(candidate_path), evaluator_path: digest(evaluator_path)},
                   "result": {"score": 2.0, "combined_score": -2.0, "direction": "minimize", "valid": True}}
    write("catalog/tasks.json", tasks)
    write("suite/index.json", {"tasks": tasks})
    write("validation/suite-report.json", {"generated": "2026-09-20T00:00:00Z", "tasks": suite_rows})
    write("validation/science-expansion-report.json", {"created_at": "2026-09-20T01:00:00Z",
          "mode": "science_expansion_validation", "tasks": [science_row, {"id": "science-blocked", "status": "blocked"}]})
    write("validation/alphaevolve-notebook-reference.json", {"results": []})
    write("validation/tensor-exact.json", {"published_decompositions": []})
    binding = {"id": "legacy-fixture", "repository": {"url": "https://github.com/example/tasks"},
               "catalog_path": "catalog/tasks.json", "index_path": "suite/index.json"}
    catalog = {"sources": [binding], "tasks": tasks}

    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True, stderr=subprocess.DEVNULL).strip()

    def commit():
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--no-gpg-sign", "-m", "fixture")
        binding["repository"]["commit"] = git("rev-parse", "HEAD")
        binding["catalog_sha256"] = digest(binding["catalog_path"])
        binding["index_sha256"] = digest(binding["index_path"])

    git("init")
    commit()
    return builder, source, catalog, write, commit


def test_builder_uses_catalog_pin_and_leaves_uncovered_or_changed_tasks_empty(source_fixture):
    builder, source, catalog, *_ = source_fixture
    data = builder.build(source, catalog)
    assert data["catalog_binding"]["repository"]["commit"] == catalog["sources"][0]["repository"]["commit"]
    assert anchor(data, "science-new", "recorded_seed_baseline")["value"] == 2.0
    for task_id in ("absent", "changed", "science-blocked"):
        assert task(data, task_id)["anchors"] == []
    assert data["summary"]["tasks_with_recorded_baseline"] == 2


def test_imported_refactor_keeps_historical_score_without_current_code_claim(source_fixture, tmp_path, monkeypatch):
    import shutil
    builder, source, catalog, *_ = source_fixture
    local = tmp_path / "tasks"
    shutil.copytree(source, local, ignore=shutil.ignore_patterns(".git"))
    originals = {path.relative_to(local).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in local.rglob("*") if path.is_file()}
    changed = "suite/science-new/evaluator.py"
    (local / changed).write_text("raise AssertionError('adapted evaluator must never execute')\n")
    (local / "import-receipt.json").write_text(json.dumps({"upstream_hashes": originals}))
    registry = tmp_path / "registry"
    registry.mkdir()
    files = {path.relative_to(local).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in local.rglob("*") if path.is_file()}
    manifest = json.dumps({"schema": "arena.task-library/1", "files": files}).encode()
    (registry / "task-library-manifest.json").write_bytes(manifest)
    old = catalog["sources"][0]
    binding = {"id": "arena-tasks", "kind": "bundled", "root_path": "tasks",
               "repository_url": "https://github.com/Doldrums/arena", "revision": "main",
               "manifest_path": "registry/task-library-manifest.json",
               "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
               **{key: old[key] for key in ("catalog_path", "index_path", "catalog_sha256", "index_sha256")}}
    catalog["sources"] = [binding]
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("No task execution or Git"))
    result = builder.build(local, catalog, registry_root=registry)
    recorded = anchor(result, "science-new", "recorded_seed_baseline")
    assert recorded["value"] == 2.0
    assert recorded["code_verification"] == "historical_code_changed"
    assert recorded["historical_code"]["changed_paths"] == [changed]
    assert "execution_identity" not in recorded
    assert recorded["historical_code"]["evaluator_sha256"] == originals[changed]
    recorded["execution_identity"] = {"source_execution": True}
    with pytest.raises(RegistryError, match="cannot claim current execution identity"):
        validate_references(result, catalog)


def test_immutable_reference_evidence_ignores_local_git_blob_replacements(source_fixture):
    builder, source, catalog, *_ = source_fixture
    expected = builder.build(source, catalog)
    pin = catalog["sources"][0]["repository"]["commit"]
    name = "suite/reference-sat/evaluator.py"
    command = ["git", "-C", str(source)]
    original = subprocess.check_output([*command, "rev-parse", f"{pin}:{name}"], text=True).strip()
    substitute = b"raise AssertionError('replacement must neither execute nor become evidence')\n"
    replacement = subprocess.check_output([*command, "hash-object", "-w", "--stdin"], input=substitute).decode().strip()
    subprocess.run([*command, "replace", original, replacement], check=True)
    assert subprocess.check_output([*command, "show", f"{pin}:{name}"]) == substitute
    assert subprocess.check_output([*command, "rev-parse", "HEAD"], text=True).strip() == pin
    assert subprocess.check_output([*command, "status", "--porcelain"], text=True).strip() == ""
    actual = builder.build(source, catalog)
    assert actual == expected
    evidence = task(actual, "reference-sat")["evaluation"]["evaluator_source"]
    assert evidence["sha256"] == hashlib.sha256((source / name).read_bytes()).hexdigest()
    assert evidence["sha256"] != hashlib.sha256(substitute).hexdigest()


@pytest.mark.parametrize("field,value", [
    ("candidate_sha256", "0" * 64), ("evaluator_sha256", "0" * 64),
    ("fixture_only", True), ("source_execution", False), ("protocol", "original"),
    ("score", 3.0),
])
def test_builder_rejects_mismatched_science_receipts(source_fixture, field, value):
    builder, source, catalog, write, commit = source_fixture
    report_path = "validation/science-expansion-report.json"
    report = json.loads((source / report_path).read_text())
    report["tasks"][0][field] = value
    write(report_path, report)
    commit()
    with pytest.raises(ValueError, match="Science receipt"):
        builder.build(source, catalog)


@pytest.mark.parametrize("change,match", [
    ("wrong_pin", "Expected task revision"), ("dirty", "modified"),
    ("catalog_digest", "Source catalog digest"), ("problem_digest", "Source problem digest"),
    ("duplicate", "Duplicate suite receipt"), ("direction", "Science receipt identity"),
    ("dependency_digest", "tracked artifact digest"),
])
def test_builder_retains_provenance_and_identity_guards(source_fixture, change, match):
    builder, source, catalog, write, commit = source_fixture
    if change == "wrong_pin":
        catalog["sources"][0]["repository"]["commit"] = "0" * 40
    elif change == "dirty":
        write("suite/reference-sat/evaluator.py", "changed tracked file\n")
    elif change == "catalog_digest":
        catalog["sources"][0]["catalog_sha256"] = "0" * 64
    elif change == "problem_digest":
        catalog["tasks"][0]["contract_source"]["sha256"] = "0" * 64
    else:
        path = "validation/suite-report.json" if change == "duplicate" else "validation/science-expansion-report.json"
        report = json.loads((source / path).read_text())
        if change == "duplicate":
            report["tasks"].append(report["tasks"][0])
        elif change == "direction":
            report["tasks"][0]["result"]["direction"] = "maximize"
        else:
            write("suite/_lib/dependency.py", "# Never imported\n")
            report["tasks"][0]["file_sha256"]["suite/_lib/dependency.py"] = "0" * 64
        write(path, report)
        commit()
    with pytest.raises(ValueError, match=match):
        builder.build(source, catalog)


def test_builder_check_detects_staleness_without_overwriting(source_fixture, tmp_path, monkeypatch):
    builder, source, catalog, *_ = source_fixture
    registry = tmp_path / "registry"
    registry.mkdir()
    output = registry / "references.json"
    output.write_text(json.dumps(builder.build(source, catalog)))
    monkeypatch.setattr(builder, "get_catalog", lambda _: catalog)
    monkeypatch.setattr(sys, "argv", ["build_references.py", str(source), "--registry", str(registry), "--check"])
    builder.main()
    output.write_text("{}\n")
    with pytest.raises(SystemExit) as error:
        builder.main()
    assert error.value.code == 1 and output.read_text() == "{}\n"


def test_builder_reads_llm_default_as_inert_source_not_a_fixed_ten(source_fixture):
    builder, source, catalog, write, commit = source_fixture
    declared = next(t for t in catalog["tasks"] if t["id"] == "absent")
    declared["family"] = "llm_benchmark"
    path = "suite/absent/problem.json"
    problem = json.loads((source / path).read_text())
    problem["family"] = "llm_benchmark"
    write(path, problem)
    declared["contract_source"]["sha256"] = hashlib.sha256((source / path).read_bytes()).hexdigest()
    write("catalog/tasks.json", catalog["tasks"])
    write("suite/_lib/autoresearch_suite/llm.py", 'raise AssertionError("must never import")\nSAMPLES = int(os.environ.get("ARTASK_LLM_SAMPLES", "7"))\n')
    commit()
    data = builder.build(source, catalog)
    row = task(data, "absent")
    assert row["evaluation"]["case_count"] == 7
    assert row["evaluation"]["case_count_kind"] == "configured_default"
    assert row["anchors"] == []
