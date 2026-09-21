# ImageNet16-120

**Paper:** LLM as a Tool, Not an Agent: Code-Mined Tree Transformations for Neural Architecture Search (https://arxiv.org/pdf/2604.16555)\
**Task id:** `llmastool-imagenet16-120`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

ImageNet16-120 task evaluated in LLM as a Tool, Not an Agent: Code-Mined Tree Transformations for Neural Architecture Search.

Benchmark named in the paper: NAS-Bench-201 and ImageNet-100 architecture search. Paper metric: classification accuracy.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `model`, domain `machine_learning`, data `public_benchmark`, verification `none`, reference `none`, resources `gpu, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness is accelerator wall-clock or model training on GPU hardware (NAS-Bench-201 and ImageNet-100 architecture search); it cannot be measured on a CPU-only suite.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `hardware:gpu`
- `dataset:NAS-Bench-201 and ImageNet-100 architecture search`

## Sources

- paper: https://arxiv.org/pdf/2604.16555 (Section 4.1)

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
