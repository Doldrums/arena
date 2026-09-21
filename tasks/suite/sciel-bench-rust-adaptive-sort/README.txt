# SCiEL: Rust adaptive sorting

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-bench-rust-adaptive-sort`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Evolve a Rust adaptive_sort implementation compiled with Cargo and benchmarked on ten generated integer datasets (random, nearly sorted, reversed, duplicate-heavy and partially sorted; 1,000 and 10,000 elements). score = 0.6*performance + 0.4*adaptability when every dataset sorts correctly, otherwise 0.

Benchmark named in the paper: SCiEL source example rust_adaptive_sort. Paper metric: score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `systems`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/rust_adaptive_sort` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- Imports openevolve.evaluation_result; suite/_lib/openevolve is a verbatim shim of that module.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `bin:cargo`
- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/rust_adaptive_sort/evaluator.py (evaluate and helper functions at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/rust_adaptive_sort/initial_program.rs (original baseline)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/rust_adaptive_sort/README.md (source README)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The pinned evaluator copies sort_test/Cargo.lock into the temporary project, but no Cargo.lock is tracked at the pinned commit (sort_test/.gitignore ignores only target/). Every evaluation therefore raises FileNotFoundError and returns score 0.0 with artifacts.error until a lock file is generated in the checkout; this repository records the defect and does not silently repair it.
