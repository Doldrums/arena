"""Pinned LLaMEA BBOB examples with explicit local-provider and pilot budgets.

The native evolutionary loop, AOCC helpers and SMAC facade are retained. Only
the example's evaluator/prompt definitions are extracted, never its main loop.
Imports are inert until an explicitly requested run.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path

from .base_gateway import MODELS

EXAMPLES = {
    False: ("examples/black-box-optimization.py", "c0e399a9ee358e331ad8f8f4a1f8bae10c1ccc45a62d491fb8f7826a4a4c8009", "evaluateBBOB"),
    True: ("examples/black-box-opt-with-HPO.py", "639801bc40be6ea560e756486cf0ab872f0ca27a62dd38fb9d23511d779430ae", "evaluateBBOBWithHPO"),
}
ENDPOINT = "http://127.0.0.1:8789/v1"


def extract_example(source: Path, hpo: bool):
    """Fail closed on source drift; return a reviewed extraction and its proof."""
    relative, digest, function = EXAMPLES[hpo]
    data = (source / relative).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Pinned LLaMEA example hash mismatch")
    tree = ast.parse(data, filename=relative)
    main = next(n for n in tree.body if isinstance(n, ast.If))
    evaluator = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == function)
    adjustments = []
    if hpo:
        # Pinned example predates the current Solution API and SMAC's string
        # instance IDs. These are compatibility fixes, not score substitutions.
        tests = [n for n in ast.walk(evaluator) if isinstance(n, ast.If)
                 and ast.unparse(n.test) == "'_configspace' not in solution.keys()"]
        if len(tests) != 1:
            raise ValueError("Expected one stale Solution dictionary check")
        tests[0].test = ast.parse("solution.configspace is None", mode="eval").body
        adjustments.append("Solution.configspace is None replaces obsolete Solution.keys()")
        budgets = [n for n in ast.walk(evaluator) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "budget" for t in n.targets)]
        if len(budgets) != 1 or ast.unparse(budgets[0].value) != "2000 * dim":
            raise ValueError("Expected the native HPO objective budget")
        budgets[0].value = ast.parse("200 * dim", mode="eval").body
        scenarios = [n for n in ast.walk(evaluator) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Name) and n.func.id == "Scenario"]
        if len(scenarios) != 1:
            raise ValueError("Expected one native SMAC Scenario")
        for kw in scenarios[0].keywords:
            if kw.arg == "n_trials":
                if not isinstance(kw.value, ast.Constant) or kw.value.value != 2000:
                    raise ValueError("Unexpected native HPO trial budget")
                kw.value = ast.Constant(value=8)
            elif kw.arg == "instances":
                if ast.unparse(kw.value) != "args":
                    raise ValueError("Unexpected native SMAC instance input")
                kw.value = ast.parse("[str(arg) for arg in args]", mode="eval").body
        adjustments += ["SMAC instance IDs normalized to strings matching native instance_features keys",
                        "Pilot: 8 SMAC trials; objective budget 200*dim=1000, matching ordinary BBOB example"]
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    prompt_names = {"task_prompt", "role_prompt", "example_prompt", "format_prompt"}
    prompts = [n for n in main.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id in prompt_names for t in n.targets)]
    extracted = ast.fix_missing_locations(ast.Module(body=imports + [evaluator] + prompts, type_ignores=[]))
    code = ast.unparse(extracted) + "\n"
    return code, {"source_path": relative, "source_sha256": digest,
                  "extracted_sha256": hashlib.sha256(code.encode()).hexdigest(),
                  "adjustments": adjustments, "function": function}


def provider(model: str):
    """Use the native OpenAI parser/query, but never pickle the scoped key."""
    if model not in MODELS:
        raise ValueError("An exact reviewed gateway model ID is required")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY must contain the scoped gateway credential")
    # Native constructor/deepcopy reads OpenAI's environment configuration.
    os.environ["OPENAI_BASE_URL"] = ENDPOINT
    from llamea import OpenAI_LLM
    import openai
    llm = OpenAI_LLM(api_key=key, model=model)
    llm.client.close()
    llm.api_key = None
    llm._client_kwargs = {"base_url": ENDPOINT, "timeout": 180, "max_retries": 0}
    llm.client = openai.OpenAI(**llm._client_kwargs)
    # Native __getstate__ omits client, and deepcopy recreates it from the
    # environment. No literal key survives in the native archive state.
    return llm


class ExampleEvaluator:
    """Pickle only the verified source text, never an executed namespace."""
    def __init__(self, code, proof):
        self.code, self.proof = code, proof
        self._function = None

    def __getstate__(self):
        return {"code": self.code, "proof": self.proof, "_function": None}

    def __call__(self, solution, explogger=None):
        if self._function is None:
            namespace = {"__name__": "arena_native_llamea_example"}
            exec(compile(self.code, self.proof["source_path"], "exec"), namespace)
            self._function = namespace[self.proof["function"]]
        return self._function(solution, explogger)


def configuration(source: Path, model: str, hpo: bool, budget: int):
    if not 2 <= budget <= 8:
        raise ValueError("Pilot native run-history budget must be between 2 and 8")
    code, proof = extract_example(source, hpo)
    namespace = {"__name__": "arena_native_llamea_example"}
    exec(compile(code, proof["source_path"], "exec"), namespace)
    kwargs = {"f": ExampleEvaluator(code, proof), "llm": provider(model),
              "n_parents": 1, "n_offspring": 1, "budget": budget,
              "max_workers": 1, "eval_timeout": 300, "elitism": True,
              "HPO": hpo, "log": True, "task_prompt": namespace["task_prompt"],
              "experiment_name": "arena-bbob-hpo-pilot" if hpo else "arena-bbob-pilot"}
    for name, target in (("role_prompt", "role_prompt"), ("example_prompt", "example_prompt"),
                         ("format_prompt", "output_format_prompt")):
        if name in namespace:
            kwargs[target] = namespace[name]
    return kwargs, proof


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--hpo", action="store_true")
    parser.add_argument("--budget", type=int, choices=range(2, 9), default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    source = Path.cwd()
    kwargs, proof = configuration(source, args.model, args.hpo, args.budget)
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=True)
    # The native logger and SMAC write relative paths. Keep all artifacts under
    # the admitted output; the clean source is never changed.
    os.chdir(output)
    (output / "provider-seam.json").write_text(json.dumps({
        "schema": "arena.native-provider-seam/1", "framework": "llamea-hpo",
        "model": args.model, "endpoint": ENDPOINT, "canonical_evaluation": False,
        "native_method": "LLaMEA", "hpo": args.hpo, "example": proof,
        "native_run_history_budget": args.budget, "parents": 1, "offspring": 1,
        "evaluation_concurrency": 1, "numeric_threads": 1,
        "provider_controls_unenforced": ["temperature"],
        "native_retries": 5, "sdk_retries": 0,
        "objective_protocol": "24 BBOB functions x 3 instances x 3 repetitions; dimension 5; 1000 evaluations",
        "hpo_trials": 8 if args.hpo else None,
    }, indent=2) + "\n")
    from llamea import LLaMEA
    LLaMEA(**kwargs).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
