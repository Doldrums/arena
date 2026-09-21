# SCiEL: Matrix multiplication rank, intended shape ⟨2,4,5⟩

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-matmul`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Construct tensor factors for rectangular matrix multiplication and minimize the reported rank. The original evaluator trusts candidate dimensions and can skip verification on empty arrays.

Benchmark named in the paper: SCiEL source example matmul. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find exact low-rank bilinear decompositions of a matrix-multiplication tensor.

Why it matters: Matrix-multiplication complexity is a substantive algebraic research problem with consequences for scientific computation. The local SCiEL instance is a restricted construction search, and its implementation status is separate from that motivation.

- [Fast Matrix Multiplication Without Tears: A Constraint Programming Approach](https://arxiv.org/abs/2306.01097): Main research objective: Find fast bilinear matrix-multiplication algorithms and certify infeasibility of proposed ranks. Task connection: The paper directly solves correctness-constrained low-rank matrix multiplication. The local task targets the intended rectangular tensor shape ⟨2,4,5⟩; the cited work studies the same formulation and does not certify this local evaluator or claim to report this exact instance.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/alphaevolve_math_problems/matmul` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:jax`
- `py:numpy`
- `py:optax`
- `py:tqdm`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/matmul/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/matmul/initial_program.py (original baseline)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The verifier returns before tensor verification if any factor array is empty. Candidate-returned n,m,p and rank determine checks/score instead of enforcing the intended fixed shape ⟨2,4,5⟩. A positive score is not evidence of a valid algorithm.
- The upstream evaluator provides no independently trusted validity boolean; a finite returned score remains unverified.
