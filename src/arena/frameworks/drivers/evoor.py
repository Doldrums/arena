"""Launch EvoOR's published initialization/evolution functions in the run copy."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

SOURCE_SHA256 = "04006f1dfaa4e3b68391945faadb462466ee39ed15ce3cacd14a9dab86862d0e"
REPLACEMENTS = (
    ('api_key=os.getenv("", "")', 'api_key=os.getenv("OPENAI_API_KEY", "")'),
    ('base_url=os.getenv("", "")', 'base_url=os.getenv("OPENAI_BASE_URL", "")'),
    ('api_key=os.getenv("")', 'api_key=os.getenv("ANTHROPIC_API_KEY", "unused-provider")'),
    ('        load_dotenv()', '        # Arena supplies the explicit run environment.'),
    ('data_path = r"c:\\Users\\Bryt\\Desktop\\end\\new_agent\\dataset\\IndustryOR_test.json"',
     'data_path = os.environ["ARENA_EVOOR_DATASET"]'),
)


def positive(value: str) -> int:
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def configure_workspace(workspace: Path, dataset: Path, output: Path) -> dict:
    """Only the reviewed configuration placeholders can change, never the scorer."""
    workspace, dataset = workspace.resolve(), dataset.resolve()
    if not dataset.is_relative_to(workspace) or not dataset.is_file():
        raise ValueError("dataset must be a regular file inside the isolated workspace")
    source = workspace / "new_utils.py"
    original = source.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("EvoOR configuration source hash mismatch")
    text = original.decode("utf-8")  # preserve the native BOM if present
    for old, new in REPLACEMENTS:
        if text.count(old) != 1:
            raise ValueError("EvoOR configuration replacement must match exactly once")
        text = text.replace(old, new)
    patched = text.encode("utf-8")
    receipt = {
        "schema": "arena.evoor-porting/1", "canonical_evaluation": False,
        "source_file": "new_utils.py", "source_sha256": digest,
        "configured_sha256": hashlib.sha256(patched).hexdigest(),
        "changes": ["restore explicit provider environment names", "disable implicit dotenv discovery",
                    "resolve the native IndustryOR dataset inside the run workspace"],
        "dataset": str(dataset.relative_to(workspace)),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "native_search_and_scoring": "unchanged",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "porting-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    source.write_bytes(patched)
    os.environ["ARENA_EVOOR_DATASET"] = str(dataset)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--model", required=True)
    parser.add_argument("--population", type=positive, required=True)
    parser.add_argument("--generations", type=positive, required=True,
                        help="Includes the initialized generation 1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.model.lower().startswith("claude"):
        parser.error("this profile uses the native OpenAI-compatible branch")
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY must be explicitly supplied in the run environment")
    if (Path.cwd() / "populations").exists():
        parser.error("fresh native populations directory required; resume is not implemented")
    configure_workspace(Path.cwd(), args.dataset, args.output)

    from initial import generate_all
    from evaluate import evolve_generation

    generate_all(num_each=args.population, model_name=args.model)
    for generation in range(2, args.generations + 1):
        evolve_generation(src_generation=generation - 1, dst_generation=generation,
                          total_offspring=args.population, model_name=args.model, seed=args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
