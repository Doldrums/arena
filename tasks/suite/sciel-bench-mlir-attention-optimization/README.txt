# SCiEL: MLIR attention transformation parameters

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-bench-mlir-attention-optimization`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Choose MLIR pass-pipeline parameters (tile sizes, vectorization, unrolling, fusion, loop interchange) for a linalg self-attention kernel. The pinned evaluator runs mlir-opt with the chosen pipeline and estimates speedup from IR statistics; error (lower is better) penalizes shortfall from a 1.32x target.

Benchmark named in the paper: SCiEL source example attention_optimization. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `configuration`, domain `systems`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/attention_optimization` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- The SCiEL evaluator (kept verbatim as evaluator_sciel.py) loads candidates only from /tmp/*.py paths; evaluator.py copies the candidate there and calls it unchanged. The pinned MLIR module targets an older MLIR release; with Homebrew LLVM 21 the seed fails to compile (tensor.expand_shape syntax), so the task reports a compilation error until a matching mlir-opt is installed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `bin:mlir-opt`
- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/attention_optimization/evaluator.py (evaluate and helper functions at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/attention_optimization/initial_program.py (original baseline)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/attention_optimization/README.md (source README)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The evaluator's own docstring states that real execution failed and that performance is estimated from IR analysis; scores are simulated, not measured kernel runtimes.
- The seed program samples parameters randomly at each call, so repeated evaluations of the same seed differ.
