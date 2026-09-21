# Non-stationary contextual bandit

**Paper:** AEL: Evolving Agent Harness in Open-Ended Environments (https://arxiv.org/pdf/2604.21725)\
**Task id:** `ael-harness-non-stationary-contextual-bandit`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Non-stationary contextual bandit

## Candidate interface

class Policy: __init__(self, n_arms, dim); select(context) -> arm; update(context, arm, reward). Non-stationary linear rewards. Score: mean per-round reward

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `machine_learning`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2604.21725 (Mechanism-validation appendices)
- repository: https://github.com/WujiangXu/AEL/tree/c95f5f961667e7df4bdddf750b22332158951bf2

## Limitations

- Support-ticket, 20Newsgroups and synthetic-bandit scripts were not found by filename in pinned tree; paper says synthetic_crossdomain.py is released, but this filename is absent.
- Named in the paper, but the corresponding task script/config is absent from the pinned public AEL tree; synthetic_crossdomain.py referenced by the paper is not present.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
