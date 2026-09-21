# Telemetry repair

**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Paper:** AdaEvolve: Adaptive LLM Driven Zeroth-Order Optimization (https://arxiv.org/pdf/2602.20133)\
**Task id:** `evox-telemetry-repair`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Telemetry repair

Benchmark named in the paper: ADRS. Paper metric: evaluator combined score.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `model`, domain `machine_learning`, data `undistributed`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate evox-telemetry-repair --route upstream --paper <paper>`.

- AdaEvolve: Telemetry repair (`adaevolve-telemetry-repair`; ADRS)

## Evaluation protocol

Not executable in this suite: The paper reports this ADRS task but the pinned public repository contains no implementation for it.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:ADRS private task`

## Sources

- paper: https://arxiv.org/pdf/2602.23413 (Systems results and task-definition appendix)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0
- paper: https://arxiv.org/pdf/2602.20133 (Systems results and task-definition appendix)

## Limitations

- Appendix task prose conflicts with standard circle-packing/Heilbronn definitions; the pinned evaluator is authoritative. Telemetry-repair directory is not present at inspected commit.
- Telemetry Repair is explicitly marked Coming soon in pinned benchmarks/ADRS/README.md; no implementation released.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
