# LLM-SQL

**Paper:** CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery (https://arxiv.org/pdf/2604.01658)\
**Paper:** AdaEvolve: Adaptive LLM Driven Zeroth-Order Optimization (https://arxiv.org/pdf/2602.20133)\
**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Task id:** `coral-llm-sql`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

LLM-SQL

Benchmark named in the paper: ADRS. Paper metric: evaluator combined score.

## Candidate interface

the row/column reordering algorithm function evaluated on the LLM-SQL datasets; score = upstream combined_score

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `systems`, data `public_benchmark`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate coral-llm-sql --route upstream --paper <paper>`.

- AdaEvolve: LLM-SQL (`adaevolve-llm-sql`; ADRS)
- EvoX: LLM-SQL (`evox-llm-sql`; ADRS)

## Evaluation protocol

Verbatim copy of the CORAL ADRS task evaluator (the same code the paper's ADRS benchmark uses); only a thin loader normalises the result.

- The released data files (eplb expert-load.json, llm_sql datasets) are not stored in the repository; `python3 scripts/prepare_adrs_data.py --suite` (and `--lock eplb-data-lock.json --suite`) fetches them at the locked revision and SHA-256 into suite/_lib/vendor/adrs. Until then the evaluator reports the missing file.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:pandas`
- `file:vendor/adrs/llm_sql/datasets/BIRD.csv`

## Sources

- paper: https://arxiv.org/pdf/2604.01658 (Section 4.1 and Table 1)
- repository: https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408 (examples/ADRS/llm_sql)
- paper: https://arxiv.org/pdf/2602.20133 (Systems results and task-definition appendix)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0 (benchmarks/ADRS/llm_sql)
- paper: https://arxiv.org/pdf/2602.23413 (Systems results and task-definition appendix)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
