"""Explicit EoB BBOB launch through its native constructors; inert on import."""
from __future__ import annotations

import argparse
import asyncio
import os


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", required=True)
    args, native_args = parser.parse_known_args(argv)
    if not args.model.startswith(("gpt", "gemini", "qwen", "deepseek")):
        parser.error("model must use a provider prefix supported by pinned LLMWrapper")
    for name in ("--N", "--generation"):
        if not any(a == name or a.startswith(name + "=") for a in native_args):
            parser.error(f"{name} must be explicitly supplied")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        parser.error("OPENAI_API_KEY must be explicitly supplied in the run environment")
    from config import get_options

    config = get_options(native_args)
    if config.task_mode != "task_bbob_expand" or config.dim not in (2, 10, 30, 50):
        parser.error("this profile supports native BBOB dimensions 2, 10, 30, 50")
    if min(config.N - 1, config.generation, config.nb_size, config.nr,
           config.n_jobs, config.algo_diff_run_time, config.algo_diff_base_FES) < 1:
        parser.error("population must be >= 2; generations, workers and evaluation budgets must be positive")
    if config.custom_data_path is not None:
        parser.error("custom data are outside the pinned BBOB profile")

    from utils.utils import LLMWrapper
    from Generator import AgenticFunctionGenerator
    from Constructor import ConstructorAgent
    from Scorer import ScoreAgent
    from Reflector import ReflectorAgent

    options = {name: getattr(config, name) for name in (
        "dim", "n_jobs", "task_mode", "selected_optimizer", "target_idx",
        "algo_diff_run_time", "algo_diff_base_FES", "custom_data_path")}
    llm = LLMWrapper(api_key=key, dim=config.dim, model=args.model)
    generator = ConstructorAgent(llm)
    reflector = ReflectorAgent(llm)
    scorer = ScoreAgent(llm, options)
    runner = AgenticFunctionGenerator(
        reflector, scorer, generator, H=config.N - 1,
        neighbor_size=config.nb_size, nr=config.nr, theta=config.theta,
        seed=config.seed, task_mode=config.task_mode)
    asyncio.run(runner.run(iterations=config.generation))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
