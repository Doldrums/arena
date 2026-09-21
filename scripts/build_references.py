#!/usr/bin/env python3
"""Build inert reference metadata from the pinned task source; never import it."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.registry import get_catalog
from arena.references import summarize, validate_references
from arena.task_source_reader import TaskSourceReader

LABELS = {
    "circle_packing_square": "Sum of circle radii in the unit square",
    "circle_packing_rectangle": "Sum of circle radii; bounding perimeter ≤ 4",
    "matmul_tensor": "Exact tensor decomposition rank",
    "heilbronn_triangle": "Minimum triangle area / enclosing equilateral triangle area",
    "heilbronn_convex": "Minimum triangle area / convex hull area",
    "max_min_distance_ratio": "Squared maximum / minimum pairwise distance ratio",
    "hexagon_packing": "Outer regular hexagon side length; inner side = 1",
    "kissing_number": "Valid integer-vector configuration size",
    "first_autocorrelation": "C1 upper bound: 2N max(convolve(h,h)) / sum(h)²",
    "second_autocorrelation": "C2 lower bound from nonnegative step heights",
    "third_autocorrelation": "Notebook C3 upper bound: abs(2N max(convolve(h,h)) / sum(h)²)",
    "signed_autocorrelation_abs": "C3′ upper bound: 2N max(abs(convolve(h,h))) / sum(h)²",
    "uncertainty_hermite": "C4 upper bound: largest positive sign-changing root² / (2π)",
    "uncertainty_laguerre": "C4 upper bound: largest positive sign-changing root / (2π)",
    "erdos_minimum_overlap": "C5 upper bound: 2 max(correlate(h,1-h)) / N",
    "sums_differences": "C6 lower bound from finite-set difference / sum cardinalities",
    "science_lj_cluster": "Total Lennard-Jones energy: 4 Σ(r⁻¹² − r⁻⁶), reduced units",
}
RAW_LABELS = {**LABELS,
    "llmsr_equation": "NMSE on the in-distribution test split",
    "ode_integrator": "−log10(relative endpoint error) − 0.5 log10(function evaluations)",
    "sat_solver": "Fraction of generated satisfiable instances solved",
}
PARAMETERS = {
    "n", "d", "dim", "dimensions", "coefficient_domain", "steps", "m", "n_lag",
    "n_instances", "n_vars", "n_nodes", "n_items", "n_jobs", "n_machines",
    "n_customers", "n_facilities", "n_constraints", "n_activities", "n_resources",
    "public_cases", "max_instances", "dataset", "benchmark", "benchmark_options",
    "seed", "problem", "split", "version", "capacity", "instance_id", "system",
}


def build(source: Path, catalog: dict, *, registry_root=None) -> dict:
    if len(catalog["sources"]) != 1:
        raise ValueError("Reference extraction requires one reviewed task collection")
    binding = catalog["sources"][0]
    reader = TaskSourceReader(source, binding, registry_root=registry_root)
    tracked = reader.paths
    contents = reader.read

    def read(path):
        return json.loads(contents(path))

    evidence = reader.evidence

    for key in ("catalog", "index"):
        if evidence(binding[f"{key}_path"], "#")["sha256"] != binding[f"{key}_sha256"]:
            raise ValueError(f"Source {key} digest does not match catalog")
    report_path = "validation/suite-report.json"
    report = read(report_path)
    def indexed(rows, label):
        result = {}
        for index, item in enumerate(rows):
            if item["id"] in result:
                raise ValueError(f"Duplicate {label} task: {item['id']}")
            result[item["id"]] = (index, item)
        return result

    smoke = indexed(report["tasks"], "suite receipt")
    science_path = "validation/science-expansion-report.json"
    science_report = read(science_path) if science_path in tracked else None
    if science_report is not None and science_report.get("mode") != "science_expansion_validation":
        raise ValueError("Unrecognized science execution report mode")
    science = indexed(science_report["tasks"], "science receipt") if science_report else {}
    imported_hashes = read("import-receipt.json").get("upstream_hashes", {}) if reader.bundled else {}
    as_of = (max(report["generated"], science_report.get("created_at", "") if science_report else "")[:10]
             if reader.bundled else subprocess.check_output(
                 [*reader.git, "show", "-s", "--format=%cs", reader.pin], text=True).strip())

    def science_receipt(row, task, evaluator_source):
        """Bind upstream execution claims to code blobs, without executing them.

        Downloaded data are deliberately not read or fetched. Their recorded
        hashes stay source assertions; only tracked code can be checked here.
        """
        task_id = task["id"]
        result = row.get("result", {})
        if (row.get("protocol") != task["protocol"] or row.get("source_execution") is not True
                or row.get("fixture_only") is not False or row.get("valid") is not True
                or result.get("valid") is not True or result.get("fixture_validation") is True
                or result.get("direction") != task["direction"] or result.get("error") is not None):
            raise ValueError(f"Science receipt identity or execution claim mismatch: {task_id}")
        if (type(row.get("score")) not in (int, float) or not math.isfinite(row["score"])
                or type(result.get("score")) not in (int, float) or row["score"] != result["score"]):
            raise ValueError(f"Science receipt score mismatch: {task_id}")
        candidate = evidence(f"suite/{task_id}/initial_program.py", "recorded seed candidate")
        hashes = row.get("file_sha256", {})
        changed = set()

        def original_digest(path, digest):
            if not reader.bundled or imported_hashes.get(path) != digest:
                raise ValueError(f"Science receipt tracked artifact digest mismatch: {task_id}: {path}")
            changed.add(path)

        for key, artifact in (("candidate_sha256", candidate), ("evaluator_sha256", evaluator_source)):
            if row.get(key) != artifact["sha256"] or hashes.get(artifact["path"]) != artifact["sha256"]:
                if row.get(key) != hashes.get(artifact["path"]):
                    raise ValueError(f"Science receipt {key} digest mismatch: {task_id}")
                original_digest(artifact["path"], row.get(key))
        for path, digest in hashes.items():
            if (not re.fullmatch(r"[0-9a-f]{64}", digest) or path.startswith("/")
                    or ".." in path.split("/") or "\\" in path):
                raise ValueError(f"Invalid science artifact identity: {task_id}")
            if path in tracked and hashlib.sha256(contents(path)).hexdigest() != digest:
                original_digest(path, digest)
            if path.endswith(".py") and path not in tracked:
                if not reader.bundled:
                    raise ValueError(f"Science receipt code is not tracked: {task_id}: {path}")
                original_digest(path, digest)
        if changed:
            return {"code_verification": "historical_code_changed", "changed_paths": sorted(changed),
                    "import_source": evidence("import-receipt.json", "#/upstream_hashes"),
                    "candidate_sha256": row["candidate_sha256"], "evaluator_sha256": row["evaluator_sha256"]}
        return {
            "source_execution": True, "fixture_only": False,
            "candidate_sha256": candidate["sha256"], "evaluator_sha256": evaluator_source["sha256"],
            "candidate_source": candidate, "evaluator_source": evaluator_source,
        }
    notebook_path = "validation/alphaevolve-notebook-reference.json"
    notebook = read(notebook_path)
    notebook_rows = {"alphaevolve-" + item["slug"]: (index, item)
                     for index, item in enumerate(notebook["results"])}
    tensor_path = "validation/tensor-exact.json"
    tensors = {tuple(item["dimensions"]): (index, item)
               for index, item in enumerate(read(tensor_path)["published_decompositions"])}
    tasks = []
    llm_samples = None
    for task in catalog["tasks"]:
        task_id = task["id"]
        problem_path = f"suite/{task_id}/problem.json"
        problem = read(problem_path)
        if evidence(problem_path, "#")["sha256"] != task["contract_source"]["sha256"]:
            raise ValueError(f"Source problem digest does not match catalog: {task_id}")
        identity_fields = ("family", "protocol") if task["protocol"] == "unsupported" else ("family", "protocol", "direction")
        if any(problem.get(key) != task.get(key) for key in identity_fields):
            raise ValueError(f"Source problem identity does not match catalog: {task_id}")
        p = problem.get("parameters", {})
        family = problem.get("family")
        evaluation = {
            "case_count": None, "case_count_kind": "not_recorded",
            "parameters": {key: value for key, value in p.items() if key in PARAMETERS},
            "seed": p.get("seed"), "dataset": p.get("dataset", p.get("benchmark")),
            "source": evidence(problem_path, "#/parameters"), "notes": [],
        }
        evaluator_path = f"suite/{task_id}/evaluator.py"
        evaluation["evaluator_source"] = evidence(evaluator_path, "evaluate / task metric definition")
        if task["protocol"] != "unsupported":
            if "n_instances" in p:
                evaluation.update(case_count=p["n_instances"], case_count_kind="declared_generated_instances")
            elif "public_cases" in p:
                evaluation.update(case_count=p["public_cases"], case_count_kind="declared_public_cases")
            elif "max_instances" in p:
                evaluation.update(case_count=p["max_instances"], case_count_kind="configured_cap")
            elif family in LABELS:
                evaluation.update(case_count=1, case_count_kind="candidate_construction")
                evaluation["notes"].append("One construction, not one statistical test observation; dimensions are in parameters.")
            elif family == "ode_integrator":
                evaluation.update(case_count=1, case_count_kind="named_initial_value_problem")
            if family == "llm_benchmark":
                llm_path = "suite/_lib/autoresearch_suite/llm.py"
                if llm_samples is None:
                    match = re.search(r'^SAMPLES = int\(os\.environ\.get\("ARTASK_LLM_SAMPLES", "([0-9]+)"\)\)$',
                                      contents(llm_path).decode(), re.MULTILINE)
                    if match is None or int(match[1]) <= 0:
                        raise ValueError("Unreviewed LLM sample default declaration")
                    llm_samples = int(match[1])
                evaluation.update(case_count=llm_samples, case_count_kind="configured_default")
                evaluation["source"] = evidence(llm_path, "SAMPLES / ARTASK_LLM_SAMPLES")
                evaluation["notes"].append("Default only: ARTASK_LLM_SAMPLES can override it; requires dataset and model. Historical seed smoke used five items.")
            if family == "llmsr_equation":
                splits = {}
                for split in ("train", "test_id", "test_ood"):
                    path = f"suite/_lib/autoresearch_suite/data/llmsr/{p['dataset']}/{split}.csv"
                    with io.StringIO(contents(path).decode(), newline="") as handle:
                        count = max(0, sum(1 for _ in csv.reader(handle)) - 1)
                    splits[split] = {"row_count": count, "source": evidence(path, "data rows, excluding header")}
                evaluation.update(case_count=splits["test_id"]["row_count"], case_count_kind="test_id_rows", splits=splits)
                evaluation["notes"].append("Parameters fit on train; score is test-ID NMSE, OOD reported separately. Search uses test-ID, so it is not an independent final audit split.")

        anchors = []
        if "published" in p:
            if family not in LABELS:
                raise ValueError(f"Unreviewed published family: {family}")
            anchor = {
                "id": task_id + ":published", "label": "Source-declared published reference",
                "kind": "published_reference", "value": p["published"],
                "metric": "score", "metric_label": LABELS[family], "score_space": "raw_task_metric",
                "direction": problem["direction"], "status": "source_reference",
                "scope": "Exact task parameters and pinned suite evaluator; not a claim about today's world best.",
                "comparison": "same_task_protocol_reference", "automatic_comparison": False,
                "reproduction": "not_recorded", "current_sota": "not_assessed", "validity": None,
                "source": evidence(problem_path, "#/parameters/published"),
                "primary_sources": problem.get("sources", []),
                "evaluation": {"case_count": 1, "case_count_kind": "candidate_construction"},
                "notes": ["Catalog-declared reference, sometimes inherited across paper packages; not necessarily that package paper's best result.",
                          "Compare only identical dimensions, coefficient domain, constraints, metric definition and evaluator; no cross-task ranking."],
            }
            if family == "matmul_tensor":
                anchor["notes"].append("Rank is restricted to the declared real or Gaussian half-integer coefficient domain; verification uses an exact integer coefficient identity.")
            if family == "max_min_distance_ratio":
                anchor["notes"].append("The local score is a SQUARED ratio, even when the paper metric label says distance ratio.")
            if family == "third_autocorrelation":
                anchor["notes"].append("Matches notebook abs(max(convolution)), not max(abs(convolution)); the signed-absolute variant is a separate task/reference.")
            if family.startswith("circle_packing"):
                anchor["notes"].append("Local geometry checks are strict; do not compare directly to a normalized SCiEL fitness or a verifier with relaxed overlap tolerances.")
            if family == "science_lj_cluster":
                anchor["notes"].append("Cambridge Cluster Database putative minimum for the stated atom count; not a proven optimum. The pinned evaluator requires pair separation ≥ 0.5 in reduced units.")
            reproduction = None
            if task_id in notebook_rows:
                index, row = notebook_rows[task_id]
                if row["published_value_from_notebook_cells"] != p["published"] or row["direction"] != problem["direction"]:
                    raise ValueError(f"Notebook receipt mismatch: {task_id}")
                reproduction = evidence(notebook_path, f"#/results/{index}/published_value_from_notebook_cells")
            elif task_id.startswith("alphaevolve-") and family == "matmul_tensor" and tuple(p["dimensions"]) in tensors:
                index, row = tensors[tuple(p["dimensions"])]
                if row["rank"] != p["published"] or row["status"] != "success":
                    raise ValueError(f"Exact tensor receipt mismatch: {task_id}")
                reproduction = evidence(tensor_path, f"#/published_decompositions/{index}")
            if reproduction:
                anchor["reproduction"] = "recorded_upstream"
                anchor["reproduction_source"] = reproduction
                anchor["notes"].append("Upstream repository contains a reference-artifact check receipt; Arena has not rerun it or reproduced the paper's search campaign.")
            anchors.append(anchor)

        receipt = smoke.get(task_id)
        identity = None
        receipt_path, recorded_at = report_path, report["generated"]
        if task_id in science:
            # The newer expansion includes changed configurations under old IDs.
            # Even a blocked expansion row supersedes any older suite score.
            index, row = science[task_id]
            receipt = None
            if row["status"] == "ok":
                identity = science_receipt(row, task, evaluation["evaluator_source"])
                receipt = (index, {**row, "direction": row["result"]["direction"],
                                   "combined_score": row["result"].get("combined_score")})
                receipt_path, recorded_at = science_path, row.get("finished_at", science_report["created_at"])
            else:
                evaluation["notes"].append("The science expansion report records no successful source execution for this configuration; an older suite score is not carried forward.")
        elif receipt is None:
            evaluation["notes"].append("The pinned suite smoke report has no row for this task; no seed score is inferred from another package.")
        elif any(receipt[1].get(key) != problem.get(key) for key in ("family", "protocol", "direction")):
            evaluation["notes"].append("The pinned suite smoke row describes a different task family, protocol or direction and is not used as a baseline for this configuration.")
            receipt = None
        if receipt is not None and receipt[1]["status"] == "ok":
            index, row = receipt
            if type(row.get("score")) not in (int, float) or not math.isfinite(row["score"]):
                raise ValueError(f"Invalid successful smoke score: {task_id}")
            anchor = {
                "id": task_id + ":seed", "label": "Recorded seed smoke baseline",
                "kind": "recorded_seed_baseline", "value": row["score"],
                "metric": "score", "metric_label": RAW_LABELS.get(family, "Recorded suite evaluator score"),
                "score_space": "raw_task_metric" if family in RAW_LABELS else "reported_score_or_selected_fitness",
                "direction": row["direction"], "status": "source_reference",
                "scope": "Historical seed-program smoke test in the source repository; not an Arena participant result or a paper benchmark result.",
                "comparison": "historical_smoke_only", "automatic_comparison": False,
                "reproduction": "not_recorded", "current_sota": "not_assessed", "validity": row.get("valid"),
                "recorded_status": row["status"], "recorded_at": recorded_at,
                "reported_combined_score": row.get("combined_score"),
                "source": evidence(receipt_path, f"#/tasks/{index}"), "primary_sources": [],
                "evaluation": {"case_count": None, "case_count_kind": "not_recorded"},
                "notes": ["Recorded score may be raw task score or wrapper-selected fitness; the report alone does not establish paper-metric equivalence.",
                          "Smoke receipts do not include complete environment, exact evaluated item IDs, repeat trials or uncertainty estimates."],
            }
            if row.get("valid") is None:
                anchor["notes"].append("status=ok means the evaluator returned a usable score; the report provides no explicit validity signal.")
            if family in RAW_LABELS:
                anchor["notes"][0] = "The pinned task evaluator exposes this raw metric. Compare only after matching the complete protocol and execution conditions."
            if identity is not None and identity.get("code_verification") == "historical_code_changed":
                anchor["code_verification"] = "historical_code_changed"
                anchor["historical_code"] = identity
                anchor["notes"].append("This score belongs to the recorded pre-import code. Arena adapted its implementation; verification of the current code is pending. It is retained as historical evidence, not a result for the current evaluator.")
            elif identity is not None:
                anchor["execution_identity"] = identity
                anchor["notes"] = [
                    "The expansion report records source execution, not a fixture-only test. Candidate, evaluator and recorded tracked-code hashes match the pinned files.",
                    "Downloaded data hashes and execution outcomes are upstream declarations; this metadata build does not fetch data or rerun candidates.",
                    "The report concerns this local task adaptation, not the source paper's full benchmark or an Arena participant run.",
                ]
            if family == "adrs_cloudcast":
                anchor["metric_label"] = "Wrapper fitness (combined_score); not raw transfer cost"
                anchor["notes"].append("Do not compare this maximizing wrapper score with the paper's cross-cloud transfer cost.")
            if family == "llm_benchmark":
                anchor["metric_label"] = "Mean per-item score on the recorded small model sample"
                anchor["evaluation"].update(case_count=5, case_count_kind="historical_smoke",
                    source=evidence("context/RESULTS.txt" if reader.bundled else "docs/RESULTS.md",
                                    "Section 1: five-item samples for model-driven tasks"))
                anchor["notes"].append("Source reports five-item Gemini 2.5 Flash smoke samples. A value of 1.0 does not mean 100% accuracy on the full named benchmark.")
            anchors.append(anchor)
        tasks.append({"task_id": task_id, "status": "source_reference" if anchors else "missing",
                      "metric": task["metric"], "direction": task["direction"], "protocol": task["protocol"],
                      "evaluation": evaluation, "anchors": anchors})
    result = {
        "schema": "arena.references/1", "as_of": as_of, "catalog_binding": binding,
        "summary": summarize(tasks), "tasks": tasks,
        "highlights": [
            {"task_id": "alphaevolve-circle-packing-in-unit-square", "reason": "A published geometric construction bound, with the number of circles and strict verifier scope."},
            {"task_id": "alphaevolve-matrix-multiplication-4-4-4", "reason": "Published rank 48 with a recorded exact-check receipt; Gaussian half-integers, not unrestricted real rank."},
            {"task_id": "coevo-oscillation-1", "reason": "Scientific symbolic regression: separate train, test-ID and OOD data; recorded seed, no extracted published numeric reference."},
            {"task_id": "dga2d-ode-solver-van-der-pol", "reason": "Numerical integration: local error/work trade-off score; recorded seed is not a paper reproduction."},
            {"task_id": "reference-sat", "reason": "Generated algorithmic test suite with an explicit instance count and seed."},
            {"task_id": "promptbreeder-gsm8k", "reason": "A model-evaluation example where sample size matters: historical five-item smoke versus configurable ten-item default."},
        ],
        "notes": ["Reference coverage counts task packages, not independent scientific problems or papers.",
                  "Current world-best results have not been assessed. Missing means no numeric anchor extracted from the pinned metadata/report, not that no literature result exists.",
                  "Science expansion receipts supersede older suite rows for the same task ID, including blocked configurations. Unmatched suite identities never supply a baseline.",
                  "All execution and reproduction evidence is recorded upstream; this snapshot build runs no evaluator, candidate, model, or benchmark."],
    }
    known_tasks = {task["id"] for task in catalog["tasks"]}
    result["highlights"] = [item for item in result["highlights"] if item["task_id"] in known_tasks]
    validate_references(result, catalog)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=ROOT / "tasks", help="Bundled task directory (default: tasks/)")
    parser.add_argument("--registry", type=Path, default=ROOT / "registry")
    parser.add_argument("--check", action="store_true", help="Fail if the committed snapshot differs; do not write files")
    args = parser.parse_args()
    data = build(args.source.resolve(), get_catalog(args.registry), registry_root=args.registry)
    output = args.registry / "references.json"
    if args.check:
        if not output.is_file() or json.loads(output.read_text()) != data:
            parser.exit(1, "Reference snapshot is stale; rebuild it from the verified task library.\n")
    else:
        output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(data["summary"], indent=2))


if __name__ == "__main__":
    main()
