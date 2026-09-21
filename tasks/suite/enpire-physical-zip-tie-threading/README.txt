# Physical zip-tie threading

**Paper:** ENPIRE: Agentic Robot Policy Self-Improvement in the Real World (https://arxiv.org/pdf/2606.19980)\
**Task id:** `enpire-physical-zip-tie-threading`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Physical zip-tie threading

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `policy`, domain `robotics`, data `real_measurements`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Evaluation runs on specialised hardware (Physical zip-tie threading) that this suite cannot provide.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `hardware:Physical zip-tie threading`

## Sources

- paper: https://research.nvidia.com/labs/gear/enpire/ (Project learned-policy demos)
- repository: https://github.com/NVlabs/ENPIRE/tree/99ee90acf65b5b18957c8382ad580db999528be3

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- Official NVIDIA project page inspected; no repository download link. RoboCasa exact task-instance list was not recovered from text; suite-level task retained.
- Official ENPIRE harness pinned (Apache-2.0); every paper task needs a physical station or a simulator that the release does not bundle.
- Requires a physical robot station and the task's perception/control services; not runnable without hardware.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
