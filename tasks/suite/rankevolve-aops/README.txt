# aops

**Paper:** RankEvolve: Automating the Discovery of Retrieval Algorithms via LLM-Driven Evolution (https://arxiv.org/pdf/2602.16932)\
**Task id:** `rankevolve-aops`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

aops task evaluated in RankEvolve: Automating the Discovery of Retrieval Algorithms via LLM-Driven Evolution.

Benchmark named in the paper: BRIGHT. Paper metric: Recall@100; nDCG@10; fitness 0.8*Recall@100+0.2*nDCG@10.

## Candidate interface

A BM25-style ranking function module (RankEvolve freeform seed) scored by the paper's evaluator on the BRIGHT split: combined_score from nDCG@10 and recall@100

Parameters: `{"dataset": "aops"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `information_retrieval`, data `public_benchmark`, verification `exact`, reference `none`, resources `network`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

The paper's pinned evaluator, executed through the repository's upstream adapter (original). The pinned source is fetched by `python3 run.py setup rankevolve-aops`; data preparation is described in the notes.

- The pinned RankEvolve loader fetches the BRIGHT documents and examples from the Hub on first use (hundreds of megabytes per split).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `checkout:fangchenli/ranking-evolved@8f664bcd5123bac2397f0c1bfbdb347ca3233483`
- `py:scipy`
- `py:datasets`
- `py:beir`
- `py:pyserini`
- `py:ir_datasets`
- `network:huggingface xlangai/BRIGHT`

## Sources

- paper: https://arxiv.org/pdf/2602.16932 (Section 4.2)
- repository: https://github.com/fangchenli/ranking-evolved/tree/8f664bcd5123bac2397f0c1bfbdb347ca3233483 (tasks/bm25/evaluator.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
