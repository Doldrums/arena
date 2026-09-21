# Anthropic performance take-home

**Paper:** CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery (https://arxiv.org/pdf/2604.01658)\
**Paper:** Harnessing Agentic Evolution (https://arxiv.org/pdf/2605.13821)\
**Task id:** `coral-anthropic-performance-take-home`\
**Protocol:** `original`\
**Direction:** minimize\

## Task

Anthropic performance take-home

## Candidate interface

class KernelBuilder with build_kernel(forest_height, n_values, n_indices, rounds) producing VLIW instructions (self.instrs) for the frozen simulator; score = cycle count of a correct kernel

Parameters: `{"forest_height": 10, "rounds": 16, "batch_size": 256, "iterations": 8}`

## Labels

Scientific contribution: `engineering` (tier 3); artifact `kernel`, domain `systems`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate coral-anthropic-performance-take-home --route upstream --paper <paper>`.

- AEvo: Anthropic performance take-home (`aevo-anthropic-performance-take-home`; Anthropic performance take-home)

## Evaluation protocol

Verbatim copy of the CORAL kernel_builder grader and frozen simulator (Anthropic performance take-home); the CORAL base classes are stubbed so the unmodified grader module can be imported.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2604.01658 (Section 4.1 stress tests)
- repository: https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408 (examples/kernel_builder)
- paper: https://arxiv.org/pdf/2605.13821 (Section 5.1; Appendix C.1)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
