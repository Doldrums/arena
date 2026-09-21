# pacemaker_2

**Paper:** Hype Meets Reality: Large Language Models as Mutators in Search-based Automated Program Repair of Simulink-Stateflow Models (https://arxiv.org/pdf/2608.19347)\
**Task id:** `llm-flowrepair-pacemaker-2`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

pacemaker_2 task evaluated in Hype Meets Reality: Large Language Models as Mutators in Search-based Automated Program Repair of Simulink-Stateflow Models.

Benchmark named in the paper: FlowRepair 19 faulty Stateflow models. Paper metric: plausible and valid patch counts across five runs.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `software_engineering`, data `undistributed`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Evaluation depends on an external toolchain (FlowRepair 19 faulty Stateflow models) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `toolchain:FlowRepair 19 faulty Stateflow models`

## Sources

- paper: https://arxiv.org/pdf/2608.19347 (Section IV-B; Tables II-IV)

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
