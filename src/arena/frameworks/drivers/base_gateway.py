"""BaSE native UCB pilot with opaque API model metadata and explicit unknown FLOPs.

Only endpoint transport and output accounting differ from native run_base.py.
LiveGreedyArm, GreedyRunner, run_base, policy and evaluator are upstream code.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import time
from types import SimpleNamespace


MODELS = ("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-6-astra",
          "gpt-5.5", "gpt-reserve", "codex-auto-review")


def omit_unsupported_seed(create, model):
    def call(**kwargs):
        if kwargs.get("model") != model:
            raise ValueError("Transport cannot substitute the selected model")
        kwargs.pop("seed", None)
        if "extra_body" in kwargs:
            raise ValueError("The gateway profile cannot send vLLM template controls")
        return create(**kwargs)
    return call


def export_arm(arm, model):
    """Native result fields; opaque model FLOPs remain unknown rather than zero."""
    runner = arm.runner
    return {"task": runner.task.key, "model": model, "model_name": model,
            "C": runner.config.C, "T": runner.config.T, "N": runner.config.N,
            "seed": runner.config.seed, "final_fitness": runner.current_fitness,
            "final_metrics": runner.current_metrics, "trajectory": runner.trajectory,
            "wall_time_seconds": round(time.time() - runner.started_at, 1) if runner.started_at else 0.0,
            "flops": None, "flops_per_generation": None, "params_active": None,
            "flops_unavailable_reason": "API model parameter count is not disclosed"}


def erase_unmeasured_flops(result):
    # run_base's absent round_flops callback uses internal logging zeros. Those
    # diagnostics never affect policy selection and must not become measurements.
    for key in ("flops_per_round", "cumulative_flops", "total_flops"):
        result[key] = None
    result["params_active"] = None
    result["flops_unavailable_reason"] = "API model parameter count is not disclosed"
    return result


async def run(args):
    from base.arms import LiveGreedyArm
    from base.runner import BaSEConfig, result_dict, run_base
    from core.llm import LLMClient
    from core.models import ModelSpec
    from core.tasks import get_task

    task = get_task("cp")
    spec = ModelSpec(key=args.model, name=args.model, params_active=None, params_total=None,
                     api_key_env="OPENAI_API_KEY", api_base_env="ARENA_BASE_GATEWAY_URL",
                     default_api_base="http://127.0.0.1:8789/v1", timeout=180, thinking=None,
                     max_tokens=8192)
    # Endpoint is operator-fixed; inherited environment cannot redirect the key.
    os.environ["ARENA_BASE_GATEWAY_URL"] = "http://127.0.0.1:8789/v1"
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must contain the scoped local gateway credential")
    llm = LLMClient(spec=spec, temperature=task.temperature)
    sdk = llm._client
    llm._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=omit_unsupported_seed(sdk.chat.completions.create, args.model))))
    config = BaSEConfig(algo="ucb", T=args.rounds, N=1, n_arms=2, parallel_llm=1)
    arms = [LiveGreedyArm(task=task, llm=llm, seed=config.arm_seed_base+i,
                          N=config.N, cap=config.T, parallel_llm=1) for i in range(config.n_arms)]
    args.output.mkdir(parents=True, exist_ok=True)
    controls = {"schema": "arena.native-provider-seam/1", "framework": "base",
                "model": args.model, "endpoint": spec.default_api_base,
                "native_search": "base.runner.run_base + LiveGreedyArm + UCB",
                "canonical_evaluation": False, "nominal_proposals": config.C,
                "native_retries_per_proposal": llm.retries,
                "provider_controls_unenforced": ["seed", "temperature", "top_p", "max_tokens"],
                "seed_note": "Native proposal seeds retained in records; API sampling seed unavailable",
                "flops_available": False, "evaluation_concurrency": 1}
    (args.output / "provider-seam.json").write_text(json.dumps(controls, indent=2)+"\n")
    started = time.time()
    trace, policy = await run_base(arms, config)
    result = result_dict(arms=arms, config=config, trace=trace, policy=policy,
                         wall_time_s=time.time()-started,
                         extra={"task": task.key, "model": args.model, "model_name": args.model,
                                "arm_results": [export_arm(arm, args.model) for arm in arms]})
    (args.output / "base-result.json").write_text(json.dumps(erase_unmeasured_flops(result), indent=2, allow_nan=False)+"\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--rounds", type=int, choices=range(1,9), default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
