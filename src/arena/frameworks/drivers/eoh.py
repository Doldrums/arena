"""Explicit launch of pinned EoH's online bin-packing example; inert on import."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from ._tls import configure_ca


def positive(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint", required=True, help="Native LLMConfig API endpoint")
    parser.add_argument("--population", type=positive, required=True)
    parser.add_argument("--generations", type=positive, required=True)
    parser.add_argument("--samples", type=positive, required=True)
    parser.add_argument("--samplers", type=positive, default=1)
    parser.add_argument("--evaluators", type=positive, default=1)
    parser.add_argument("--eval-timeout", type=positive, default=40)
    parser.add_argument("--tls-ca", type=Path, help="Verified public CA bundle supplied as a hashed run input")
    parser.add_argument("--numeric-threads", type=positive, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if any(c in args.endpoint for c in "/@\r\n"):
        parser.error("endpoint must be an HTTPS hostname, without scheme, path or credentials")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        parser.error("OPENAI_API_KEY must be explicitly supplied in the run environment")
    configure_ca(args.tls_ca)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = str(args.numeric_threads)
    # CWD is the verified native example directory; no arbitrary module name is accepted.
    sys.path.insert(0, str(Path.cwd()))
    sys.path.insert(0, str(Path.cwd().parents[1] / "eoh" / "src"))
    from eoh import EoH, LLMConfig
    from prob import BPONLINE

    llm = LLMConfig(api_endpoint=args.endpoint, api_key=key, model=args.model, timeout=150)
    task = BPONLINE(capacity=100, timeout=args.eval_timeout)
    method = EoH(llm=llm, problem=task, pop_size=args.population,
                 n_pop=args.generations, max_sample_nums=args.samples,
                 num_samplers=args.samplers, num_evaluators=args.evaluators,
                 output_dir=str(args.output))
    method.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
