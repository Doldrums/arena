"""Native EoH-S set-search pilot using its packaged OBP training data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from .base_gateway import MODELS
from ._tls import configure_ca
from .meoh import environment_key_provider

DATASET = "datasets/obp/dataset_100_2k_128_5_80_training.pkl"


def configuration(model: str, output: Path, dataset: Path, samples: int = 8):
    if model not in MODELS or not 6 <= samples <= 16:
        raise ValueError("Use an exact gateway model and 6..16 registered samples")
    from llm4ad.task.optimization.online_bin_packing_set import OBPSEvaluation
    from llm4ad.tools.llm.llm_api_https import HttpsApi
    from llm4ad.method.eohs import EoHSProfiler
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY must contain the scoped gateway credential")
    return {
        "llm": environment_key_provider(HttpsApi)(host="127.0.0.1:8790", key=key, model=model, timeout=180),
        "evaluation": OBPSEvaluation(timeout_seconds=120, dataset=str(dataset), return_list=True),
        "profiler": EoHSProfiler(log_dir=str(output), log_style="simple"),
        "max_sample_nums": samples, "max_generations": 4, "pop_size": 2,
        "num_samplers": 1, "num_evaluators": 1, "debug_mode": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--samples", type=int, choices=range(6, 17), default=8)
    parser.add_argument("--tls-ca", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    configure_ca(args.tls_ca)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(output / ".matplotlib")
    dataset = Path(DATASET).absolute()
    kwargs = configuration(args.model, output, dataset, args.samples)
    (output / "provider-seam.json").write_text(json.dumps({
        "schema": "arena.native-provider-seam/1", "framework": "eoh-s", "model": args.model,
        "endpoint": "https://127.0.0.1:8790/v1", "canonical_evaluation": False,
        "task": "native online bin packing heuristic-set evaluation",
        "dataset_path": DATASET, "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "max_registered_samples": args.samples, "max_generations": 4, "population": 2,
        "evaluation_concurrency": 1, "numeric_threads": 1,
        "provider_controls_unenforced": ["temperature", "top_p", "max_tokens"],
        "limits": "Native parse failures and HTTP retries do not all increment sample count; outer wall timeout is authoritative.",
    }, indent=2) + "\n")
    from llm4ad.method.eohs import EoHS
    EoHS(**kwargs).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
