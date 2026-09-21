#!/usr/bin/env python3
"""Fetch the text-adventure game files used by the text_game family into suite/_lib/data (git-ignored).

* Jericho game suite ROMs (github.com/BYU-PCCL/z-machine-games, pinned commit,
  SHA-256 per file) for the Learning-to-Learn-at-Test-Time tasks;
* TextWorld games generated locally with ``tw-make`` and fixed seeds for the
  BALROG/HSI TextWorld task (treasure hunter, coin collector, cooking).

    python3 scripts/prepare_game_data.py
"""
from __future__ import annotations

import sys as _task_sys
from pathlib import Path as _TaskPath
_task_sys.path.insert(0, str(_TaskPath(__file__).resolve().parents[1] / "suite" / "_lib"))
from arena_task_paths import data_root

import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = data_root()
COMMIT = "bfd7544aa1f50549fc327bd4eb3bc8144bfd80ea"
BASE = f"https://raw.githubusercontent.com/BYU-PCCL/z-machine-games/{COMMIT}/jericho-game-suite/"
ROMS = {"balances.z5": "10e717578f85200c6aadc8149d95e43f7b6c09fb473770d309a0d6afe3b29538", "detective.z5": "f6b0b9b5f4ff8890ab481b11e63ea18350b43640c88a9b8c23d6a2b269f9a040",
        "library.z5": "b3665eaf5e30520355a1f07657ffbd69e967ecb53942f86913d044e65fa30e11", "temple.z5": "7378f6ce08153beb2f75b05054b70c4c4589a34c4f6f6295349115359dfb326f",
        "zork1.z5": "0ae5ac229e79094ff368b6669356444af0f35e21d862a1baaa546989085c15fd", "zork3.z5": "dce7e6f757fb8379dea9da9c13cdda5412ba03fa9b70d79fb6b8c7faf5970692"}
TEXTWORLD = {"treasure_hunter.z8": ["tw-treasure_hunter", "--level", "8", "--seed", "11"],
             "coin_collector.z8": ["tw-coin_collector", "--level", "10", "--seed", "23"],
             "cooking.z8": ["tw-cooking", "--recipe", "2", "--take", "1", "--go", "6", "--open", "--cook", "--seed", "37"]}


def main():
    folder = DATA / "jericho"
    folder.mkdir(parents=True, exist_ok=True)
    for name, digest in ROMS.items():
        path = folder / name
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            continue
        with urllib.request.urlopen(BASE + name, timeout=120) as response:
            raw = response.read()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError(f"{name}: SHA-256 differs from the pinned value")
        path.write_bytes(raw)
    print(f"jericho: {len(ROMS)} games")
    tw_make = shutil.which("tw-make") or str(Path(sys.executable).with_name("tw-make"))
    if not Path(tw_make).is_file():
        print("textworld: tw-make not found (pip install textworld); TextWorld games not generated")
        return
    folder = DATA / "textworld"
    folder.mkdir(parents=True, exist_ok=True)
    for name, args in TEXTWORLD.items():
        path = folder / name
        if path.is_file():
            continue
        subprocess.run([tw_make, *args, "--output", str(path)], check=True, capture_output=True, text=True)
    print(f"textworld: {len(TEXTWORLD)} games")


if __name__ == "__main__":
    main()
