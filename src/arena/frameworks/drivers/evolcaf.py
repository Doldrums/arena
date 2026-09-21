"""Launch the authentic historical EvolCAF example through its native EoH API."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def positive(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True, help="Native HTTPS API hostname")
    parser.add_argument("--model", required=True)
    parser.add_argument("--population", type=positive, required=True)
    parser.add_argument("--generations", type=positive, required=True)
    parser.add_argument("--processes", type=positive, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        parser.error("OPENAI_API_KEY must be explicitly supplied in the run environment")
    # This profile runs in examples/user_bo_caf of the separately pinned old revision.
    sys.path.insert(0, str(Path.cwd()))
    sys.path.insert(0, str(Path.cwd().parents[1] / "eoh" / "src"))
    from eoh import eoh
    from eoh.utils.getParas import Paras
    from prob import Evaluation

    parameters = Paras()
    parameters.set_paras(method="eoh", problem=Evaluation(),
                         llm_api_endpoint=args.endpoint, llm_api_key=key, llm_model=args.model,
                         ec_pop_size=args.population, ec_n_pop=args.generations,
                         exp_n_proc=args.processes, exp_debug_mode=False,
                         eva_numba_decorator=False, exp_output_path=str(args.output))
    eoh.EVOL(parameters).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
