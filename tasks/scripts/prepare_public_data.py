#!/usr/bin/env python3
"""Fetch the public data files the suite evaluators read from suite/_lib/data (git-ignored).

* ARC-AGI-1 (fchollet/ARC-AGI) and ARC-AGI-2 (arcprize/ARC-AGI-2) task JSON,
  converted to the Kaggle layout (arc-agi_<split>_challenges.json and
  arc-agi_<split>_solutions.json) under suite/_lib/data/arc-agi-1 and
  suite/_lib/data/arc-prize-2025;
* the 24 Instruction Induction execution sets (orhonovich/instruction-induction,
  data/raw/execute) under suite/_lib/data/instruction-induction.

    python3 scripts/prepare_public_data.py
"""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import data_root

import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = data_root()
ARC = {"arc-agi-1": "https://github.com/fchollet/ARC-AGI.git", "arc-prize-2025": "https://github.com/arcprize/ARC-AGI-2.git"}
II_TASKS = ["active_to_passive", "antonyms", "cause_and_effect", "common_concept", "diff", "first_word_letter", "informal_to_formal", "larger_animal", "letters_list",
            "negation", "num_to_verbal", "orthography_starts_with", "rhymes", "second_word_letter", "sentence_similarity", "sentiment", "singular_to_plural", "sum",
            "synonyms", "taxonomy_animal", "translation_en-de", "translation_en-es", "translation_en-fr", "word_in_context"]
II_URL = "https://raw.githubusercontent.com/orhonovich/instruction-induction/main/data/raw/execute/{}.json"


def convert_arc(clone, target):
    for split in ("training", "evaluation"):
        challenges, solutions = {}, {}
        for path in sorted((clone / "data" / split).glob("*.json")):
            task = json.loads(path.read_text())
            challenges[path.stem] = {"train": task["train"], "test": [{"input": t["input"]} for t in task["test"]]}
            solutions[path.stem] = [t["output"] for t in task["test"]]
        (target / f"arc-agi_{split}_challenges.json").write_text(json.dumps(challenges))
        (target / f"arc-agi_{split}_solutions.json").write_text(json.dumps(solutions))
        print(f"{target.name}/{split}: {len(challenges)} tasks")


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    for name, url in ARC.items():
        clone = DATA / url.rsplit("/", 1)[1].removesuffix(".git")
        if not clone.is_dir():
            subprocess.run(["git", "clone", "-q", "--depth", "1", url, str(clone)], check=True)
        target = DATA / name
        target.mkdir(exist_ok=True)
        convert_arc(clone, target)
    folder = DATA / "instruction-induction"
    folder.mkdir(exist_ok=True)
    for task in II_TASKS:
        path = folder / f"{task}.json"
        if not path.is_file():
            with urllib.request.urlopen(II_URL.format(task), timeout=60) as response:
                path.write_bytes(response.read())
    print(f"instruction-induction: {len(list(folder.glob('*.json')))} tasks")


if __name__ == "__main__":
    main()
