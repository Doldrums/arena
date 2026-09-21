# Binary Search

**Paper:** EvoPrompting: Language Models for Code-Level Neural Architecture Search (https://arxiv.org/pdf/2302.14838)\
**Task id:** `evoprompting-binary-search`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Evaluate the discovered graph-neural-network architecture on the CLRS Binary Search algorithmic reasoning problem, including out-of-distribution sequence lengths.

Benchmark named in the paper: CLRS. Paper metric: OOD accuracy and parameter count.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `model`, domain `machine_learning`, data `public_benchmark`, verification `none`, reference `none`, resources `gpu, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness is accelerator wall-clock or model training on GPU hardware (CLRS); it cannot be measured on a CPU-only suite.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `hardware:gpu`
- `dataset:CLRS`

## Sources

- paper: https://arxiv.org/pdf/2302.14838 (Section 4.2 and Appendix Table 3)

## Limitations

- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
