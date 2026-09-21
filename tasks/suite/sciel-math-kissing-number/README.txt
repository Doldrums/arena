# SCiEL: Kissing number in dimension 11

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-kissing-number`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Construct an integral point configuration in 11 dimensions satisfying the upstream norm and distance checks and maximize its size.

Benchmark named in the paper: SCiEL source example kissing_number. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct large eleven-dimensional kissing configurations of nonoverlapping spheres.

Why it matters: Kissing configurations establish lower bounds in discrete geometry and are related to spherical codes. Each additional validated sphere can strengthen a mathematical packing bound; the local score is not a general AI benchmark metric.

- [Finding Kissing Numbers with Game-theoretic Reinforcement Learning](https://arxiv.org/abs/2511.13391): Main research objective: Discover sphere configurations giving stronger kissing-number lower bounds. Task connection: The paper directly constructs kissing configurations to improve kissing-number bounds. This local task fixes dimension eleven and restricts its representation; the paper establishes the primary problem pursued, without implying that its reported improvements occur in dimension eleven.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/alphaevolve_math_problems/kissing_number` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/kissing_number/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/kissing_number/initial_program.py (original baseline)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The upstream evaluator provides no independently trusted validity boolean; a finite returned score remains unverified.
