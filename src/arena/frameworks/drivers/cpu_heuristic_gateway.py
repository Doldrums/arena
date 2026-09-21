"""Launch the verified native Hydra entrypoint; no alternate search algorithm."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import runpy
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--engine", choices=("reevo", "hsevo", "mcts-ahd"), required=True)
    parser.add_argument("native", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    native_args = args.native[1:] if args.native[:1] == ["--"] else args.native
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must contain the scoped local gateway credential")
    # The staged native YAML selects the exact model; only HSEvo uses this env
    # endpoint seam. ReEvo/MCTS receive base_url through their native constructor.
    if args.engine == "hsevo":
        os.environ["OPENAI_API_BASE"] = "http://127.0.0.1:8789/v1"
    proof = {"schema": "arena.native-provider-seam/1", "framework": args.engine,
             "endpoint": "http://127.0.0.1:8789/v1", "canonical_evaluation": False,
             "native_entrypoint": "main.py", "native_loop_modified": False,
             "provider_controls_unenforced": ["temperature", "max_tokens", "top_p"],
             "batch_transport": "ordered sequential n=1 draws" if args.engine == "reevo" else "native",
             "budget_note": "Native max_fe is an outer progress target; retries and whole generations may exceed it. The operator enforces the wall timeout."}
    Path("arena-provider-seam.json").write_text(json.dumps(proof, indent=2)+"\n")
    entrypoint = Path.cwd() / "main.py"
    sys.argv = [str(entrypoint), *native_args]
    runpy.run_path(str(entrypoint), run_name="__main__")


if __name__ == "__main__":
    main()
