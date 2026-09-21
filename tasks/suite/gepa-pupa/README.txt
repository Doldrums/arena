# PUPA

**Paper:** GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning (https://arxiv.org/pdf/2507.19457)\
**Paper:** Reward-Free Evolving Agents via Pairwise Validator (https://arxiv.org/pdf/2607.14408)\
**Task id:** `gepa-pupa`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

PUPA

Benchmark named in the paper: PUPA. Paper metric: task-specific score.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate gepa-pupa --route upstream --paper <paper>`.

- Pairwise Validator: PUPA (`pairwise-validator-pupa`; PUPA)

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the PUPA benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:PUPA`

## Sources

- paper: https://arxiv.org/pdf/2507.19457 (Section 4 evaluation and benchmark appendix)
- repository: https://github.com/gepa-ai/gepa-artifact/tree/cbefbc1aa0f43dd39874ec4bf42211365dbda42e (gepa_artifact/benchmarks/papillon)
- paper: https://arxiv.org/pdf/2607.14408 (Section 5, Table 1 task inventory)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
