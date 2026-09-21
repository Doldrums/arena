# Balanced incomplete block design (CSPLib 28)

**Paper:** LLM-Guided Evolutionary Search for Constraint Model Reformulation to Improve Solver Efficiency (https://arxiv.org/pdf/2607.28268)\
**Task id:** `pdr-balanced-incomplete-block-design-csplib-28`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Balanced incomplete block design (CSPLib 28) task evaluated in LLM-Guided Evolutionary Search for Constraint Model Reformulation to Improve Solver Efficiency.

Benchmark named in the paper: CSPLib / AutoIG. Paper metric: geometric mean baseline-relative runtime speedup (PAR2 for timeout).

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `public_benchmark`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Evaluation depends on an external toolchain (CSPLib / AutoIG) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `toolchain:CSPLib / AutoIG`

## Sources

- paper: https://arxiv.org/pdf/2607.28268 (Section 5, Experimental setup)

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
