"""Explicit launch of LLM4AD MEoH; native two-objective evaluation is unchanged."""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def positive(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="HTTPS host without a scheme")
    parser.add_argument("--model", required=True)
    parser.add_argument("--population", type=positive, required=True)
    parser.add_argument("--generations", type=positive, required=True)
    parser.add_argument("--samples", type=positive, required=True)
    parser.add_argument("--samplers", type=positive, default=1)
    parser.add_argument("--evaluators", type=positive, default=1)
    parser.add_argument("--eval-timeout", type=positive, default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if any(c in args.host for c in "/@\r\n"):
        parser.error("host must be a hostname, without scheme, path or credentials")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        parser.error("OPENAI_API_KEY must be explicitly supplied in the run environment")
    from llm4ad.task.optimization.online_bin_packing_2O import OBP_2O_Evaluation
    from llm4ad.tools.llm.llm_api_https import HttpsApi
    from llm4ad.method.meoh import MEoH, MEoHProfiler

    method = MEoH(
        llm=HttpsApi(host=args.host, key=key, model=args.model, timeout=120),
        evaluation=OBP_2O_Evaluation(timeout_seconds=args.eval_timeout),
        profiler=MEoHProfiler(log_dir=str(args.output), num_objs=2, log_style="simple"),
        max_sample_nums=args.samples, max_generations=args.generations,
        pop_size=args.population, num_samplers=args.samplers,
        num_evaluators=args.evaluators, num_objs=2, debug_mode=False,
    )
    method.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
