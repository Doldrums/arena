#!/usr/bin/env python3
"""Build inert reference metadata from the pinned task source; never import it."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from arena.registry import get_catalog
from arena.references import summarize, validate_references

PIN = "995768fc462b8e327f90e6762846cc6ccb06cc2c"
REPOSITORY = "https://github.com/IMRUNya/autoresearch-tasks"
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


def build(source: Path, catalog: dict) -> dict:
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if revision != PIN:
        raise ValueError(f"Expected task revision {PIN}, got {revision}")
    if subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise ValueError("Tracked source files are modified; pinned evidence must be clean")
    binding = next(item for item in catalog["sources"] if item["id"] == "autoresearch-tasks")
    if binding["repository"] != {"url": REPOSITORY, "commit": PIN}:
        raise ValueError("Catalog source does not match the pinned reference source")

    def read(path):
        return json.loads((source / path).read_text())

    def evidence(path, locator):
        return {"path": path, "url": f"{REPOSITORY}/blob/{PIN}/{path}",
                "sha256": hashlib.sha256((source / path).read_bytes()).hexdigest(), "locator": locator}

    for key in ("catalog", "index"):
        if evidence(binding[f"{key}_path"], "#")["sha256"] != binding[f"{key}_sha256"]:
            raise ValueError(f"Source {key} digest does not match catalog")
    report_path = "validation/suite-report.json"
    report = read(report_path)
    smoke = {item["id"]: (index, item) for index, item in enumerate(report["tasks"])}
    notebook_path = "validation/alphaevolve-notebook-reference.json"
    notebook = read(notebook_path)
    notebook_rows = {"alphaevolve-" + item["slug"]: (index, item)
                     for index, item in enumerate(notebook["results"])}
    tensor_path = "validation/tensor-exact.json"
    tensors = {tuple(item["dimensions"]): (index, item)
               for index, item in enumerate(read(tensor_path)["published_decompositions"])}
    tasks = []
    for task in catalog["tasks"]:
        task_id = task["id"]
        problem_path = f"suite/{task_id}/problem.json"
        problem = read(problem_path)
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
                evaluation.update(case_count=10, case_count_kind="configured_default")
                evaluation["source"] = evidence("suite/_lib/autoresearch_suite/llm.py", "SAMPLES / ARTASK_LLM_SAMPLES")
                evaluation["notes"].append("Default only: ARTASK_LLM_SAMPLES can override it; requires dataset and model. Historical seed smoke used five items.")
            if family == "llmsr_equation":
                splits = {}
                for split in ("train", "test_id", "test_ood"):
                    path = f"suite/_lib/autoresearch_suite/data/llmsr/{p['dataset']}/{split}.csv"
                    with (source / path).open(newline="") as handle:
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

        index, row = smoke[task_id]
        if row["status"] == "ok" and isinstance(row.get("score"), (int, float)):
            anchor = {
                "id": task_id + ":seed", "label": "Recorded seed smoke baseline",
                "kind": "recorded_seed_baseline", "value": row["score"],
                "metric": "score", "metric_label": RAW_LABELS.get(family, "Recorded suite evaluator score"),
                "score_space": "raw_task_metric" if family in RAW_LABELS else "reported_score_or_selected_fitness",
                "direction": row["direction"], "status": "source_reference",
                "scope": "Historical seed-program smoke test in the source repository; not an Arena participant result or a paper benchmark result.",
                "comparison": "historical_smoke_only", "automatic_comparison": False,
                "reproduction": "not_recorded", "current_sota": "not_assessed", "validity": row.get("valid"),
                "recorded_status": row["status"], "recorded_at": report["generated"],
                "reported_combined_score": row.get("combined_score"),
                "source": evidence(report_path, f"#/tasks/{index}"), "primary_sources": [],
                "evaluation": {"case_count": None, "case_count_kind": "not_recorded"},
                "notes": ["Recorded score may be raw task score or wrapper-selected fitness; the report alone does not establish paper-metric equivalence.",
                          "Smoke receipts do not include complete environment, exact evaluated item IDs, repeat trials or uncertainty estimates."],
            }
            if row.get("valid") is None:
                anchor["notes"].append("status=ok means the evaluator returned a usable score; the report provides no explicit validity signal.")
            if family in RAW_LABELS:
                anchor["notes"][0] = "The pinned task evaluator exposes this raw metric. Compare only after matching the complete protocol and execution conditions."
            if family == "adrs_cloudcast":
                anchor["metric_label"] = "Wrapper fitness (combined_score); not raw transfer cost"
                anchor["notes"].append("Do not compare this maximizing wrapper score with the paper's cross-cloud transfer cost.")
            if family == "llm_benchmark":
                anchor["metric_label"] = "Mean per-item score on the recorded small model sample"
                anchor["evaluation"].update(case_count=5, case_count_kind="historical_smoke",
                    source=evidence("docs/RESULTS.md", "Section 1: five-item samples for model-driven tasks"))
                anchor["notes"].append("Source reports five-item Gemini 2.5 Flash smoke samples. A value of 1.0 does not mean 100% accuracy on the full named benchmark.")
            anchors.append(anchor)
        tasks.append({"task_id": task_id, "status": "source_reference" if anchors else "missing",
                      "metric": task["metric"], "direction": task["direction"], "protocol": task["protocol"],
                      "evaluation": evaluation, "anchors": anchors})
    result = {
        "schema": "arena.references/1", "as_of": "2026-09-20", "catalog_binding": binding,
        "summary": summarize(tasks), "tasks": tasks,
        "highlights": [
            {"task_id": "alphaevolve-circle-packing-in-unit-square", "reason": "A published geometric construction bound, with the number of circles and strict verifier scope."},
            {"task_id": "alphaevolve-matrix-multiplication-4-4-4", "reason": "Published rank 48 with a recorded exact-check receipt; Gaussian half-integers, not unrestricted real rank."},
            {"task_id": "coevo-oscillation-1", "reason": "Scientific symbolic regression: separate train, test-ID and OOD data; recorded seed, no extracted published numeric reference."},
            {"task_id": "a2dept-ode-integration-van-der-pol-oscillator", "reason": "Numerical integration: local error/work trade-off score; recorded seed is not a paper reproduction."},
            {"task_id": "reference-sat", "reason": "Generated algorithmic test suite with an explicit instance count and seed."},
            {"task_id": "promptbreeder-gsm8k", "reason": "A model-evaluation example where sample size matters: historical five-item smoke versus configurable ten-item default."},
        ],
        "notes": ["Reference coverage counts task packages, not independent scientific problems or papers.",
                  "Current world-best results have not been assessed. Missing means no numeric anchor extracted from the pinned metadata/report, not that no literature result exists.",
                  "All execution and reproduction evidence is recorded upstream; this snapshot build runs no evaluator, candidate, model, or benchmark."],
    }
    validate_references(result, catalog)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Clean checkout of the pinned task repository")
    parser.add_argument("--registry", type=Path, default=ROOT / "registry")
    args = parser.parse_args()
    data = build(args.source.resolve(), get_catalog(args.registry))
    (args.registry / "references.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(data["summary"], indent=2))


if __name__ == "__main__":
    main()
