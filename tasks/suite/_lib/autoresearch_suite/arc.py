"""ARC-AGI program-synthesis tasks scored on the public ARC data (recreated protocol).

Data: the public ARC-AGI-1 (fchollet/ARC-AGI) and ARC-AGI-2 (arcprize/ARC-AGI-2)
repositories, converted to the Kaggle JSON layout under
``suite/_lib/data/{arc-agi-1,arc-prize-2025}``. The candidate exposes

    solve(task, llm) -> list of output grids (one per test input)

where ``task`` is ``{"train": [{"input", "output"}, ...], "test": [{"input"}, ...]}``
and ``llm`` is the budgeted model client. Score: fraction of test grids
reproduced exactly over a fixed, seeded sample of evaluation tasks.
"""
from __future__ import annotations

from arena_task_paths import data_root

import json
import random
from pathlib import Path

from .llm import LLM, DEFAULT_MODEL, BUDGET_USD, SAMPLES
from .runtime import CandidateError, require

DATA = data_root()


def load_tasks(version, split="evaluation"):
    folder = DATA / ("arc-prize-2025" if version == 2 else "arc-agi-1")
    challenges = folder / f"arc-agi_{split}_challenges.json"
    solutions = folder / f"arc-agi_{split}_solutions.json"
    require(challenges.is_file() and solutions.is_file(), f"ARC data missing under {folder}; clone the public ARC-AGI repositories into suite/_lib/data")
    tasks = json.loads(challenges.read_text())
    answers = json.loads(solutions.read_text())
    return {tid: {"train": t["train"], "test": t["test"], "answers": answers[tid]} for tid, t in tasks.items()}


def grid_equal(a, b):
    try:
        return [[int(v) for v in row] for row in a] == [[int(v) for v in row] for row in b]
    except (TypeError, ValueError):
        return False


def arc_score(solve, version=2, split="evaluation", n_samples=None, seed=0, model=None, budget_usd=None):
    tasks = load_tasks(version, split)
    ids = sorted(tasks)
    random.Random(seed).shuffle(ids)
    chosen = ids[: (n_samples or max(3, SAMPLES // 2))]
    llm = LLM(model=model or DEFAULT_MODEL, budget_usd=BUDGET_USD if budget_usd is None else budget_usd, max_tokens=4096)
    correct = total = 0
    crashes = 0
    for tid in chosen:
        task = tasks[tid]
        try:
            outputs = solve({"train": task["train"], "test": task["test"]}, llm)
        except CandidateError:
            raise
        except Exception:  # noqa: BLE001
            crashes += 1
            outputs = []
        for index, answer in enumerate(task["answers"]):
            total += 1
            if isinstance(outputs, (list, tuple)) and index < len(outputs) and grid_equal(outputs[index], answer):
                correct += 1
    return {"score": correct / total if total else 0.0, "tasks": len(chosen), "test_grids": total, "crashes": crashes, "usage": llm.usage()}
