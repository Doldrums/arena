#!/usr/bin/env python3
"""Create seven versioned, bounded MCTS-AHD plans; never launch native research."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from arena.frameworks.drivers.mcts_ahd_gateway_v2 import COMMIT, SIGNATURE

MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra", "gpt-5.5", "gpt-reserve", "codex-auto-review")
PROFILE = "gateway-cpu-pilot-v2"
FRAMEWORK = "mcts-ahd-gateway-v2"
ORIGINAL_SIGNATURE_SHA256 = "1fe62833cda697a5ba228b2782f9965abf9e11cc969dba2b60934b3dbcf0d58c"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def configured(source, model):
    if model not in MODELS:
        raise ValueError("Choose an exact reviewed gateway model")
    original = (source / "prompts/bpp_online/func_signature.txt").read_bytes()
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SIGNATURE_SHA256:
        raise ValueError("The pinned original signature changed")
    config = (source / "cfg/config.yaml").read_text()
    for key, value in dict(max_fe=4, pop_size=2, init_pop_size=2, timeout=60).items():
        config, count = re.subn(r"(?m)^" + key + r":[^\n]*$", key + ": " + str(value), config)
        if count != 1:
            raise ValueError("Missing or ambiguous native configuration field: " + key)
    client = {"_target_": "utils.llm_client.openai.OpenAIClient", "model": model,
              "temperature": 1.0, "base_url": "http://127.0.0.1:8789/v1",
              "api_key": "${oc.env:OPENAI_API_KEY}"}
    return {"cfg/config.yaml": config,
            "cfg/llm_client/openai.yaml": json.dumps(client, indent=2) + "\n",
            "prompts/bpp_online/func_signature.txt": SIGNATURE + "\n"}


def prepare(root, destination):
    from arena.frameworks.runtime import prepare_plan, verify_source
    if not root.is_absolute() or not destination.is_absolute() or destination.exists():
        raise ValueError("Absolute root and a new absolute destination are required")
    source = root / "sources/mcts-ahd"
    revision = verify_source(source, COMMIT)
    destination.mkdir(parents=True, mode=0o750)
    templates, records = [], []
    for model in MODELS:
        slug = model.replace(".", "-")
        directory = destination / slug
        directory.mkdir(mode=0o750)
        overlays = {}
        for relative, content in configured(source, model).items():
            path = directory / relative.replace("/", "--")
            path.write_text(content)
            overlays[relative] = str(path)
        request = {"python": str(root / "envs/mcts-ahd/bin/python"), "profile": PROFILE,
                   "arguments": [], "config_overlays": overlays}
        spec = {"schema": "arena.native-run/1", "framework": FRAMEWORK, "source_dir": str(source),
                "output_dir": str(root / "runs" / destination.name / slug), "timeout_seconds": 2400,
                "request": request, "environment_names": ["OPENAI_API_KEY"]}
        plan = prepare_plan(spec)
        write_json(directory / "native-run.json", spec)
        write_json(directory / "plan.json", plan)
        templates.append({"id": "cpu-mcts-ahd-v2-" + slug, "name": "MCTS-AHD bounded v2 CPU pilot · " + model,
                          "framework": FRAMEWORK, "profile": PROFILE, "model": model,
                          "status": "ready", "blocked_reason": None,
                          "resources": {"cpus": 4, "memory_mb": 8192, "evaluation_slots": 1, "pids": 512},
                          "containment": "cgroup-v2", "evaluation_concurrency_verified": True,
                          "spec": {**spec, "output_dir": "{output_dir}"}})
        records.append({"model": model, "source": revision, "plan_sha256": plan["sha256"],
                        "plan_path": str(directory / "plan.json"), "research_executed": False,
                        "canonical_evaluation": False})
    write_json(destination / "templates.json", templates)
    evidence = {"schema": "arena.mcts-pilot-preparation/2", "records": records,
                "replaces_profile_for_new_pilots": "gateway-cpu-pilot", "originals_modified": False,
                "proposal_limit": 8, "initialization_limit": 3, "native_max_fe_target": 4,
                "initial_population": 2, "outer_timeout_seconds": 2400,
                "budget_basis": "A healthy initialization consumes two proposals; the first native tree round calls e2 once, m1 twice and m2 twice. Its s1 path is skipped for a root child. At most three initialization proposals leave five of the eight slots for that round; failures/duplicates can exhaust the pilot earlier. Native parser/SDK retries and post-thought requests are not separate proposal attempts.",
                "concurrency_basis": "Native Problem.batch_evaluate waits for each single-candidate subprocess; numerical thread environment is fixed to one. Generated code remains within the admitted worker cgroup.",
                "provider": {"endpoint": "http://127.0.0.1:8789/v1", "compatibility_policy": "codex-native",
                             "unenforced_controls": ["temperature", "max_tokens", "top_p"],
                             "credentials": "OPENAI_API_KEY environment reference only"},
                "limits": ["No native research or provider call is performed by preparation.",
                           "The v2 attempt guard is explicit pilot instrumentation. Budget exhaustion exits75 and retains partial evidence without claiming completion.",
                           "Fixed-response parser/evaluator conformance is separate from scientific results.",
                           "This uses native evaluation, not canonical Arena evaluation or hostile-code Docker isolation."]}
    write_json(destination / "preparation.json", evidence)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("/srv/arena"))
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    evidence = prepare(args.root, args.destination)
    print(json.dumps({"records": len(evidence["records"]), "destination": str(args.destination), "research_executed": False}))


if __name__ == "__main__":
    main()
