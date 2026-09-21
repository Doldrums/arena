# Formal Fallacies

**Paper:** PhaseEvo: Towards Unified In-Context Prompt Optimization for Large Language Models (https://arxiv.org/pdf/2402.11347)\
**Paper:** EvoPrompt: Connecting LLMs with Evolutionary Algorithms Yields Powerful Prompt Optimizers (https://arxiv.org/pdf/2309.08532)\
**Task id:** `phaseevo-formal-fallacies`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Formal Fallacies: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: BBH. Paper metric: accuracy.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "bbh", "benchmark_options": {"task": "formal_fallacies"}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate phaseevo-formal-fallacies --route upstream --paper <paper>`.

- EvoPrompt: BBH formal_fallacies (`evoprompt-bbh-formal-fallacies`; BIG-Bench Hard, formal_fallacies)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Model-driven evaluation: the score depends on the model (ARTASK_LLM_MODEL, default google/gemini-2.5-flash), the sample size (ARTASK_LLM_SAMPLES, default 10) and the per-evaluation budget (ARTASK_LLM_BUDGET_USD, default 0.25). Responses are cached under .cache/llm-cache.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:datasets`
- `env:OPENROUTER_API_KEY`
- `network:openrouter+huggingface`

## Sources

- paper: https://arxiv.org/pdf/2402.11347 (BBH results table; current arXiv v2)
- paper: https://arxiv.org/pdf/2309.08532 (Appendix C.2, Tables 17-18)
- repository: https://github.com/beeevita/EvoPrompt/tree/94caff336555df99acc5c338c7930c40cc550ad9 (BBH/eval.py)

## Limitations

- arXiv latest HTML is v2 titled SEE (2025); original PhaseEvo v1 HTML/PDF returned HTTP 406. Original OpenReview manuscript confirms the same 35-task suite, but version-specific protocol differences must be checked before reproduction.
- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
