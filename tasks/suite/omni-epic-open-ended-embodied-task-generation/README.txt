# Open-ended embodied task generation

**Paper:** OMNI-EPIC: Open-endedness via Models of human Notions of Interestingness with Environments Programmed in Code (https://arxiv.org/pdf/2405.15568)\
**Task id:** `omni-epic-open-ended-embodied-task-generation`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Open-ended embodied task generation: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: OMNI-EPIC PyBullet environments. Paper metric: task diversity and learnability.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `environment`, domain `games`, data `simulator`, verification `none`, reference `none`, resources `simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires a physics simulator or reinforcement-learning training loop (OMNI-EPIC PyBullet environments) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `environment:OMNI-EPIC PyBullet environments`

## Sources

- paper: https://arxiv.org/pdf/2405.15568 (Experiments)
- repository: https://github.com/maxencefaldor/omni-epic/tree/af2a3c64f40bc48178c08e1beb76a0aafdd2a167 (main_omni_epic.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
