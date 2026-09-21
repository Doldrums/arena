"""Explicit Julia LaSR library launch; no native imports or installs in Python."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess

JULIA_ENTRY = r'''
using JSON
using LibraryAugmentedSymbolicRegression
data_path, model, iterations, populations, probability, output = ARGS
data = JSON.parsefile(data_path)
X = reduce(hcat, [Float64.(row) for row in data["X"]])
y = Float64.(data["y"])
p = parse(Float64, probability)
options = LaSROptions(;
    binary_operators=[+, -, *, /, ^], unary_operators=[cos],
    populations=parse(Int, populations), use_llm=true, use_concepts=true,
    use_concept_evolution=true,
    llm_operation_weights=LLMOperationWeights(;
        llm_crossover=p, llm_mutate=p, llm_randomize=p),
    prompts_dir=joinpath(pwd(), "prompts"),
    api_key=ENV["OPENAI_API_KEY"], model=model,
    api_kwargs=Dict("url"=>ENV["OPENAI_BASE_URL"]), verbose=false)
hall = equation_search(X, y; niterations=parse(Int, iterations),
                       options=options, parallelism=:multithreading)
frontier = [Dict("equation"=>string_tree(m.tree, options),
                 "loss"=>(isfinite(m.loss) ? m.loss : Dict("nonfinite"=>string(m.loss))),
                 "complexity"=>compute_complexity(m, options))
            for m in calculate_pareto_frontier(hall)]
open(joinpath(output, "native-frontier.json"), "w") do io
    JSON.print(io, Dict("schema"=>"arena.lasr-native/1", "canonical_evaluation"=>false,
                       "native"=>Dict("pareto_frontier"=>frontier)))
end
'''


def positive(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def read_data(path: Path) -> dict:
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("LaSR dataset exceeds 16 MiB")
    data = json.loads(path.read_text())
    if type(data) is not dict or set(data) != {"X", "y"}:
        raise ValueError("LaSR dataset must contain exactly X and y")
    x, y = data["X"], data["y"]
    if type(x) is not list or type(y) is not list or not 2 <= len(x) <= 100000 or len(x) != len(y):
        raise ValueError("X rows and y must have the same length, from 2 to 100000")
    if type(x[0]) is not list or not 1 <= len(x[0]) <= 100:
        raise ValueError("X must have 1 to 100 features")
    if any(type(row) is not list or len(row) != len(x[0]) for row in x):
        raise ValueError("X must be rectangular")
    if any(type(v) not in (float, int) or not math.isfinite(v) for row in x for v in row) or any(
            type(v) not in (float, int) or not math.isfinite(v) for v in y):
        raise ValueError("LaSR dataset must contain finite numeric values")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--julia", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--iterations", type=positive, required=True)
    parser.add_argument("--populations", type=positive, required=True)
    parser.add_argument("--llm-probability", type=float, default=0.0001)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.julia.is_absolute() or not args.julia.is_file() or not os.access(args.julia, os.X_OK):
        parser.error("--julia must name the explicit executable recorded by the run plan")
    if not math.isfinite(args.llm_probability) or not 0 <= args.llm_probability <= 1:
        parser.error("--llm-probability must be in [0, 1]")
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL"):
        if not os.environ.get(name):
            parser.error(f"{name} must be explicitly supplied in the run environment")
    data = read_data(args.data)
    args.output.mkdir(parents=True, exist_ok=True)
    # Serialize validated data once; no model or user string becomes Julia source code.
    dataset = args.output / "input-data.json"
    dataset.write_text(json.dumps(data, allow_nan=False))
    entry = args.output / "native-entry.jl"
    entry.write_text(JULIA_ENTRY)
    command = [str(args.julia), "--startup-file=no", f"--project={Path.cwd()}", str(entry),
               str(dataset), args.model, str(args.iterations), str(args.populations),
               str(args.llm_probability), str(args.output)]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
