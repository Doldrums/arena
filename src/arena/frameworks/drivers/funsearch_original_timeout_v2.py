"""Original FunSearch pilot v2: bounded client deadline above the gateway deadline.

The original native pipeline and scorer are delegated unchanged. Importing this
module does not load a native framework, create a client or execute a candidate.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import funsearch_gateway as gateway
from .base_gateway import MODELS

REQUEST_TIMEOUT = 330
GATEWAY_TIMEOUT = 300
MAX_SAMPLES = 6
OUTER_TIMEOUT = 2400


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--bubblewrap", type=Path, required=True)
    parser.add_argument("--max-samples", type=int, choices=(MAX_SAMPLES,), default=MAX_SAMPLES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("A scoped local gateway key is required")
    args.output.mkdir(parents=True, exist_ok=True)
    if any(args.output.iterdir()):
        raise ValueError("Pilot results directory must be empty")
    proof = {
        "schema": "arena.funsearch-gateway-pilot/2", "engine": "original",
        "recipe": "funsearch-original-timeout-v2", "model": args.model,
        "endpoint": gateway.GATEWAY, "provider_model_alias_substituted": False,
        "native_search_and_scoring": True, "canonical_evaluation": False,
        "generated_sample_budget": MAX_SAMPLES, "additional_native_validation_calls": 0,
        "evaluation_concurrency": 1,
        "transport": {"sdk_timeout_seconds": REQUEST_TIMEOUT, "sdk_max_retries": 0,
                      "expected_gateway_timeout_seconds": GATEWAY_TIMEOUT,
                      "template_outer_timeout_seconds": OUTER_TIMEOUT,
                      "timeout_scope": "OpenAI SDK per-operation timeout; outer process-group bound is enforced by Arena runtime",
                      "gateway_timeout_scope": "Operator-configured gateway request deadline; not reconfigured or measured by this driver"},
        "namespace_sandbox": {"network": False, "host_credentials_mounted": False,
                              "address_space_bytes": 2 * 1024**3, "wall_timeout_seconds": 30},
        "task": {"kind": "constant-weight admissible set", "input": [9, 5]},
        "provider_controls_unenforced": [],
    }
    (args.output / "provider-seam.json").write_text(json.dumps(proof, indent=2) + "\n")
    return gateway.original(args, request_timeout=REQUEST_TIMEOUT)


if __name__ == "__main__":
    raise SystemExit(main())
