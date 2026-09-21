# XLA auto-sharding IOPDDL

**Paper:** Magellan: Autonomous Discovery of Novel Compiler Optimization Heuristics with AlphaEvolve (https://arxiv.org/pdf/2601.21096)\
**Task id:** `magellan-xla-auto-sharding-iopddl`\
**Protocol:** `unsupported`\
**Direction:** minimize\

## Task

XLA auto-sharding IOPDDL task evaluated in Magellan: Autonomous Discovery of Novel Compiler Optimization Heuristics with AlphaEvolve.

Benchmark named in the paper: XLA auto-sharding IOPDDL. Paper metric: contest objective under memory constraints.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `systems`, data `public_benchmark`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Evaluation depends on an external toolchain (XLA auto-sharding IOPDDL) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `toolchain:XLA auto-sharding IOPDDL`

## Sources

- paper: https://arxiv.org/pdf/2601.21096 (Sections 3.1-3.3)

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
