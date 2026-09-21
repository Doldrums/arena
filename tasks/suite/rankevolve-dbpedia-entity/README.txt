# dbpedia-entity

**Paper:** RankEvolve: Automating the Discovery of Retrieval Algorithms via LLM-Driven Evolution (https://arxiv.org/pdf/2602.16932)\
**Task id:** `rankevolve-dbpedia-entity`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

dbpedia-entity task evaluated in RankEvolve: Automating the Discovery of Retrieval Algorithms via LLM-Driven Evolution.

Benchmark named in the paper: BEIR. Paper metric: Recall@100; nDCG@10; fitness 0.8*Recall@100+0.2*nDCG@10.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `information_retrieval`, data `undistributed`, verification `none`, reference `none`, resources `unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires the BEIR data and training pipeline, which are not redistributed with the suite.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:BEIR`

## Sources

- paper: https://arxiv.org/pdf/2602.16932 (Section 4.2)
- repository: https://github.com/fangchenli/ranking-evolved/tree/8f664bcd5123bac2397f0c1bfbdb347ca3233483 (tasks/bm25/evaluator.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
