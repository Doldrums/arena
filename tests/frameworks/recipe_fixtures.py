"""Load an ordered recipe family for its existing offline conformance tests."""
import json


def recipe_group(root, group):
    paths = sorted((root / "registry/framework-recipes").glob(f"{group}.*.json"))
    if not paths:
        raise AssertionError(f"Missing recipe family: {group}")
    recipes = []
    for path in paths:
        document = json.loads(path.read_text())
        assert document["schema"] == "arena.framework-recipes/1", path
        recipes.extend(document["recipes"])
    return {"schema": "arena.framework-recipes/1", "recipes": recipes}
