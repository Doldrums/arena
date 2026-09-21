"""Explicit native-framework integrations, separate from the read-only board.

Importing this package never imports a participant, starts a run or evaluates a
candidate. Native scores are not canonical Arena evaluation receipts.
"""
from importlib import import_module


FRAMEWORKS = {
    "sciel": ("SCiEL", "SCiELAdapter"),
    "shinka": ("ShinkaEvolve", "ShinkaAdapter"),
    "dgm": ("Darwin Gödel Machine", "DGMAdapter"),
}


def get_adapter(framework):
    if framework not in FRAMEWORKS:
        from .recipes import RecipeAdapter, load_recipes
        recipes = load_recipes()
        recipe = recipes.get(framework)
        if recipe is None:
            candidates = [r for r in recipes.values() if framework in r["participant_ids"] and r["profiles"]]
            if len(candidates) != 1:
                raise ValueError(f"Choose an explicit native engine for {framework!r}: {[r['id'] for r in candidates]}")
            recipe = candidates[0]
        if not recipe["profiles"]:
            raise ValueError(recipe["blocked_reason"] or "No executable profile in this source artifact")
        return RecipeAdapter(recipe, identity=framework)
    module = import_module(f"arena.frameworks.{framework}")
    return getattr(module, FRAMEWORKS[framework][1])()


def describe():
    from .recipes import load_recipes
    native = [{"id": ident, "name": name, "commit": get_adapter(ident).commit,
             "adapter_status": "native_cli", "runtime_readiness": "not_verified",
             "canonical_evaluation": False, "pause": False, "resume": False}
            for ident, (name, _) in FRAMEWORKS.items()]
    return native + [{"id": r["id"], "name": r["name"], "repository": r["repository"],
                     "participant_ids": r["participant_ids"], "source_status": r["status"],
                     "adapter_status": "native_cli" if r["profiles"] else "not_implemented",
                     "runtime_readiness": "not_verified", "canonical_evaluation": False,
                     "pause": False, "resume": False, "profiles": r["profiles"],
                     "setup": r["setup"], "limitations": r["blocked_reason"]}
                    for r in load_recipes().values()]
