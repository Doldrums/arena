# Terrain-conditioned Sodarace synthesis

**Paper:** Evolution through Large Models (https://arxiv.org/pdf/2206.08896)\
**Task id:** `elm-terrain-conditioned-sodarace-synthesis`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Terrain-conditioned Sodarace synthesis: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Terrain-conditioned Sodarace synthesis. Paper metric: horizontal distance / terrain return / repair accuracy respectively.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `games`, data `simulator`, verification `none`, reference `none`, resources `simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Sodarace walkers are simulated with the Sodaracer Box2D environment.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `environment:Sodarace`

## Sources

- paper: https://arxiv.org/pdf/2206.08896 (Sections 4–7 and Appendix A)

## Limitations

- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
