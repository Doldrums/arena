"""Explicit data-to-native-run bridge for pinned LLM-LEx; no optimizer of its own."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path


def positive(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def read_xy(path: Path) -> tuple[list[float], list[float]]:
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("data JSON exceeds 16 MiB")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"x", "y"}:
        raise ValueError("data must contain exactly x and y numeric arrays")
    for key in ("x", "y"):
        values = data[key]
        if not isinstance(values, list) or not 2 <= len(values) <= 100000:
            raise ValueError("x and y must have 2 to 100000 samples")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError("x and y must contain finite numbers")
    if len(data["x"]) != len(data["y"]):
        raise ValueError("x and y lengths must match")
    return data["x"], data["y"]


def serializable_native(value):
    """Retain native JSON values and numeric arrays; never evaluate saved formulae."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else {"nonfinite": str(value)}
    if isinstance(value, (list, tuple)):
        return [serializable_native(v) for v in value]
    if isinstance(value, dict):
        return {str(k): serializable_native(v) for k, v in value.items()}
    # Called only for live native results after an explicitly requested run.
    if type(value).__module__.split('.')[0] == "numpy" and hasattr(value, "tolist"):
        return serializable_native(value.tolist())
    return {"omitted_type": type(value).__name__}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="JSON with x and y arrays")
    parser.add_argument("--model", required=True)
    parser.add_argument("--population", type=positive, required=True)
    parser.add_argument("--generations", type=positive, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        x_values, y_values = read_xy(args.data)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        parser.error("OPENAI_API_KEY must be explicitly supplied in the run environment")
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import openai
    import llmlex

    client = openai.OpenAI(api_key=key, base_url=os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"))
    x, y = np.asarray(x_values, dtype=float), np.asarray(y_values, dtype=float)
    fig, ax = plt.subplots()
    try:
        ax.scatter(x, y)
        image = llmlex.images.generate_base64_image(fig, ax, x, y)
    finally:
        plt.close(fig)
    populations = llmlex.run_genetic(client, image, x, y, population_size=args.population,
                                     num_of_generations=args.generations, model=args.model)
    args.output.mkdir(parents=True, exist_ok=True)
    artifact = {"schema": "arena.native-result/1", "framework": "llm-lex",
                "canonical_evaluation": False,
                "native": {"populations": serializable_native(populations)},
                "warnings": ["Scores are native negative normalized chi-squared; no held-out evaluation is added."]}
    (args.output / "native-populations.json").write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
