# HoVer

**Paper:** Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs (https://arxiv.org/pdf/2406.11695)\
**Paper:** GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning (https://arxiv.org/pdf/2507.19457)\
**Paper:** Reward-Free Evolving Agents via Pairwise Validator (https://arxiv.org/pdf/2607.14408)\
**Task id:** `mipro-hover`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

HoVer: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: HoVer. Paper metric: Recall@21.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate mipro-hover --route upstream --paper <paper>`.

- GEPA: HoVer (`gepa-hover`; HoVer)
- Pairwise Validator: HoVer (`pairwise-validator-hover`; HoVer)

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the HoVer benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:HoVer`

## Sources

- paper: https://arxiv.org/pdf/2406.11695 (Table 1 and Appendices A/E)
- repository: https://github.com/stanfordnlp/dspy/tree/40a6e168914a7b81a78b1a081d93f26de18c8d0d
- paper: https://arxiv.org/pdf/2507.19457 (Section 4 evaluation and benchmark appendix)
- repository: https://github.com/gepa-ai/gepa-artifact/tree/cbefbc1aa0f43dd39874ec4bf42211365dbda42e (gepa_artifact/benchmarks/hover)
- paper: https://arxiv.org/pdf/2607.14408 (Section 5, Table 1 task inventory)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Current DSPy repository has MIPROv2 optimizer but the seven original 2024 benchmark drivers were not located in the inspected tree; API library availability alone does not make original tasks executable.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
