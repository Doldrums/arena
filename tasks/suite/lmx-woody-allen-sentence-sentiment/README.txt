# Woody Allen sentence sentiment

**Paper:** Language Model Crossover: Variation through Few-Shot Prompting (https://arxiv.org/pdf/2302.12170)\
**Task id:** `lmx-woody-allen-sentence-sentiment`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Woody Allen sentence sentiment: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Woody Allen sentence sentiment. Paper metric: domain-specific fitness / QD score.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the Woody Allen sentence sentiment benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:Woody Allen sentence sentiment`

## Sources

- paper: https://arxiv.org/pdf/2302.12170 (Sections 4.1–4.5)
- repository: https://github.com/jal278/lmx/tree/b8fec5dd16451cf7afb6e02ac621b71d5bdfee7f (scripts/lmx_sentiment_demo.ipynb)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
