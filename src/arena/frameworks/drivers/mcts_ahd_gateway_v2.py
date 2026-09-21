"""Versioned, bounded MCTS-AHD pilot; preserve native search and evaluation."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

COMMIT = "ee9c4f424503c65a5fd2b899e6620ce86079fedb"
SIGNATURE = "def priority_v{version}(item: float, bins_remain_cap: np.ndarray) -> np.ndarray:"
SOURCE_HASHES = {
    "main.py": "3b7d820cac801da0d31914147bdde28035bc1f071ebb7afab8c53c9f244516a1",
    "source/evolution_interface.py": "7bc8661d5b7200dbb15290f8225b7fb4eec49ca3dbc946d3e563bcf116e56135",
    "source/evolution.py": "45deb5af2e0bfe7bce31a60003b1d4d0946affbf6a9ceed943a544d76512048c",
    "source/mcts_ahd.py": "70122ce89fcae1c7c39d18db676fd874b79e9000b32d91abc2154e5a3eacf51d",
    "source/getParas.py": "a65afbb1119f33553e631cd42babf4af1f9930ebf97d7ccc92ec815cd9327065",
    "problem_adapter.py": "5e12d1fd312dc48bacbc4e32b843089ad1434f8ec99c7db3d22a55209c6cbfa5",
    "problems/bpp_online/eval.py": "507cfc8cfebba2dfa20ad926df222eb3a473353e528a1c6ea15711d6d7bc58fc",
}


class ProposalBudgetExhausted(BaseException):
    """Escape native `except Exception: retry` without claiming completion."""


class AttemptBudget:
    def __init__(self, total: int, initialization: int, path: Path):
        if type(total) is not int or not 1 <= total <= 64:
            raise ValueError("Proposal budget must be an integer in 1..64")
        if type(initialization) is not int or not 1 <= initialization <= total:
            raise ValueError("Initialization budget must be in 1..proposal budget")
        self.total, self.initialization, self.path = total, initialization, path
        self.depth = 0
        self.events = []
        self.status = "prepared"
        self.exhausted = None

    def save(self):
        value = {"schema": "arena.mcts-pilot-attempts/2", "status": self.status,
                 "proposal_limit": self.total, "initialization_limit": self.initialization,
                 "attempt_count": len(self.events),
                 "initialization_attempt_count": sum(e["phase"] == "initialization" for e in self.events),
                 "exhausted": self.exhausted, "attempts": self.events,
                 "canonical_evaluation": False,
                 "count_scope": "Native InterfaceEC._get_alg entries, including failed parser/transport attempts and duplicate-code retries; not HTTP calls or billed requests."}
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
        temporary.replace(self.path)

    def before(self, operator):
        initial = sum(e["phase"] == "initialization" for e in self.events)
        reason = "total" if len(self.events) >= self.total else "initialization" if self.depth and initial >= self.initialization else None
        if reason:
            self.status, self.exhausted = "budget_exhausted", reason
            self.save()
            raise ProposalBudgetExhausted(reason)
        self.events.append({"attempt": len(self.events) + 1,
                            "phase": "initialization" if self.depth else "search", "operator": operator})
        self.status = "running"
        self.save()


@contextmanager
def bounded_native_attempts(interface_class, budget):
    """Wrap admission to native operators; keep original method bodies intact."""
    original_alg = interface_class._get_alg
    original_init = interface_class.get_algorithm

    def get_alg(instance, pop, operator, father=None):
        budget.before(operator)
        return original_alg(instance, pop, operator, father=father)

    def get_algorithm(instance, *args, **kwargs):
        budget.depth += 1
        try:
            return original_init(instance, *args, **kwargs)
        finally:
            budget.depth -= 1

    interface_class._get_alg = get_alg
    interface_class.get_algorithm = get_algorithm
    try:
        yield
    finally:
        interface_class._get_alg = original_alg
        interface_class.get_algorithm = original_init


def verify_workspace(root):
    for relative, expected in SOURCE_HASHES.items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError("MCTS-AHD source seam changed: " + relative)
    if (root / "prompts/bpp_online/func_signature.txt").read_text().strip() != SIGNATURE:
        raise ValueError("The v2 BPP prompt must request priority_v{version}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--attempt-budget", type=int, default=8, choices=[8])
    parser.add_argument("--init-attempt-budget", type=int, default=3, choices=[3])
    args = parser.parse_args(argv)
    root = Path.cwd()
    verify_workspace(root)
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY must contain the scoped gateway credential")
    # Imports occur only during explicit execution, after immutable-source checks.
    from source.evolution_interface import InterfaceEC
    proof = {"schema": "arena.native-provider-seam/2", "framework": "mcts-ahd",
             "profile": "gateway-cpu-pilot-v2", "source_commit": COMMIT,
             "endpoint": "http://127.0.0.1:8789/v1", "canonical_evaluation": False,
             "native_entrypoint": "main.py", "native_search_operators_modified": False,
             "native_parser_modified": False, "native_evaluator_modified": False,
             "pilot_hooks": ["Prompt function name matches evaluator priority_v2 import", "Admission guard around native InterfaceEC._get_alg"],
             "proposal_budget": args.attempt_budget, "initialization_budget": args.init_attempt_budget,
             "native_max_fe_target": 4, "native_initial_population": 2,
             "budget_note": "Two successful initialization proposals plus five native operator attempts fit a complete first tree round. Parser/SDK retries and post-thought calls remain native; proposal counts are not API-call or billing counts. Exhaustion exits 75 without reporting native completion.",
             "provider_controls_unenforced": ["temperature", "max_tokens", "top_p"]}
    (root / "arena-provider-seam-v2.json").write_text(json.dumps(proof, indent=2) + "\n")
    budget = AttemptBudget(args.attempt_budget, args.init_attempt_budget, root / "arena-attempt-budget-v2.json")
    budget.save()
    previous_argv = sys.argv
    sys.argv = [str(root / "main.py"), "algorithm=mcts_ahd", "problem=bpp_online",
                "max_fe=4", "init_pop_size=2", "pop_size=2", "timeout=60"]
    try:
        with bounded_native_attempts(InterfaceEC, budget):
            runpy.run_path(str(root / "main.py"), run_name="__main__")
    except ProposalBudgetExhausted:
        return 75
    except BaseException:
        budget.status = "native_error"
        budget.save()
        raise
    else:
        budget.status = "native_returned"
        budget.save()
        return 0
    finally:
        sys.argv = previous_argv


if __name__ == "__main__":
    raise SystemExit(main())
