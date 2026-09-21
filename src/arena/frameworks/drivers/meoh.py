"""Explicit launch of LLM4AD MEoH; native two-objective evaluation is unchanged."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from ._tls import configure_ca


def positive(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def environment_key_provider(native_class):
    """Keep the native request implementation while excluding its key from logs.

    The pinned MEoH profiler prints every provider ``__dict__`` value. Its
    native HttpsApi reads ``self._key`` only when constructing Authorization;
    this property avoids ever adding that credential to the logged dictionary.
    """
    class EnvironmentKeyHttpsApi(native_class):
        @property
        def _key(self):
            return os.environ["OPENAI_API_KEY"]

        @_key.setter
        def _key(self, value):
            if value != os.environ.get("OPENAI_API_KEY"):
                raise ValueError("Provider key must come from OPENAI_API_KEY")

    return EnvironmentKeyHttpsApi


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
    parser.add_argument("--tls-ca", type=Path, help="Verified public CA bundle supplied as a hashed run input")
    parser.add_argument("--numeric-threads", type=positive, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if any(c in args.host for c in "/@\r\n"):
        parser.error("host must be a hostname, without scheme, path or credentials")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        parser.error("OPENAI_API_KEY must be explicitly supplied in the run environment")
    configure_ca(args.tls_ca)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = str(args.numeric_threads)
    os.environ["MPLCONFIGDIR"] = str(args.output.absolute() / ".arena" / "matplotlib")
    from llm4ad.task.optimization.online_bin_packing_2O import OBP_2O_Evaluation
    from llm4ad.tools.llm.llm_api_https import HttpsApi
    from llm4ad.method.meoh import MEoH, MEoHProfiler

    method = MEoH(
        llm=environment_key_provider(HttpsApi)(host=args.host, key=key, model=args.model, timeout=120),
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
