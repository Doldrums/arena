# MNIST-1D architecture search

**Paper:** EvoPrompting: Language Models for Code-Level Neural Architecture Search (https://arxiv.org/pdf/2302.14838)\
**Task id:** `evoprompting-mnist-1d-architecture-search`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

MNIST-1D architecture search: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: MNIST-1D architecture search. Paper metric: test error and parameter count.

## Candidate interface

build_model() -> torch.nn.Module mapping (batch, 40) float inputs to (batch, 10) logits, with at most MAX_PARAMETERS parameters. The evaluator trains it with Adam (lr 1e-3, batch 128, STEPS steps) on the deterministic MNIST-1D training set and reports test_error + 0.05 * parameters / 100000. Lower is better.

Parameters: `{"steps": 1500, "max_parameters": 250000, "seed": 0}`

## Labels

Scientific contribution: `engineering` (tier 3); artifact `model`, domain `machine_learning`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- EvoPrompting's MNIST-1D setting recreated on the CPU: the mnist1d package regenerates the dataset deterministically; the training budget and the size penalty are local choices (the paper reports test error and parameter count).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:torch`
- `py:mnist1d`

## Sources

- paper: https://arxiv.org/pdf/2302.14838 (Section 4.1)

## Limitations

- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
