# Datacenter TCP congestion control

**Paper:** AdaEvolve: Adaptive LLM Driven Zeroth-Order Optimization (https://arxiv.org/pdf/2602.20133)\
**Task id:** `adaevolve-datacenter-tcp-congestion-control`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Datacenter TCP congestion control

Benchmark named in the paper: ADRS NS3. Paper metric: throughput and queue latency.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `systems`, data `undistributed`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

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

- paper: https://arxiv.org/pdf/2602.20133 (Appendix B Table 6)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0

## Limitations

- Paper reports datacenter TCP congestion control, but no task implementation or selector exists in the pinned public repository tree.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
