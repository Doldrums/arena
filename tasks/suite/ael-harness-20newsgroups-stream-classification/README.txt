# 20Newsgroups stream classification

**Paper:** AEL: Evolving Agent Harness in Open-Ended Environments (https://arxiv.org/pdf/2604.21725)\
**Task id:** `ael-harness-20newsgroups-stream-classification`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

20Newsgroups stream classification

Benchmark named in the paper: 20Newsgroups. Paper metric: classification accuracy.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `language`, data `undistributed`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: The AEL harness task needs its market / ticket / 20Newsgroups data streams, which are not distributed with the pinned tree.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:20Newsgroups`

## Sources

- paper: https://arxiv.org/pdf/2604.21725 (Cross-domain appendix)
- repository: https://github.com/WujiangXu/AEL/tree/c95f5f961667e7df4bdddf750b22332158951bf2

## Limitations

- Support-ticket, 20Newsgroups and synthetic-bandit scripts were not found by filename in pinned tree; paper says synthetic_crossdomain.py is released, but this filename is absent.
- Named in the paper, but the corresponding task script/config is absent from the pinned public AEL tree; synthetic_crossdomain.py referenced by the paper is not present.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
