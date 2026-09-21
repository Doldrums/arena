# Sarcasm

**Paper:** Automatic Prompt Optimization with “Gradient Descent” and Beam Search (https://arxiv.org/pdf/2305.03495)\
**Paper:** PhaseEvo: Towards Unified In-Context Prompt Optimization for Large Language Models (https://arxiv.org/pdf/2402.11347)\
**Task id:** `protegi-sarcasm`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Sarcasm: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Sarcasm. Paper metric: F1.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "sarcasm", "benchmark_options": {}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate protegi-sarcasm --route upstream --paper <paper>`.

- PhaseEvo: Sarcasm (`phaseevo-sarcasm`; Sarcasm, Sarcasm)

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

- paper: https://arxiv.org/pdf/2305.03495 (Section 4)
- repository: https://github.com/microsoft/LMOps/tree/6f53ef41c951de0962bbf27fe3f5819eabc8ce0e (prompt_optimization/main.py)
- paper: https://arxiv.org/pdf/2402.11347 (Experiments and Appendix E.1)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Code expects the API key in config.OPENAI_KEY, not the OPENAI_API_KEY environment variable, and hardcodes historical model names. No repository dependency manifest for this subproject was found.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
