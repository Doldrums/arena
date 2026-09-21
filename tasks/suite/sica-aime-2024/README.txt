# AIME 2024

**Paper:** A Self-Improving Coding Agent (https://arxiv.org/pdf/2504.15228)\
**Paper:** Reward-Free Evolving Agents via Pairwise Validator (https://arxiv.org/pdf/2607.14408)\
**Paper:** ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution (https://arxiv.org/pdf/2509.19349)\
**Task id:** `sica-aime-2024`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

AIME 2024: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: AIME 2024. Paper metric: benchmark score; time and API cost enter combined utility.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "aime24", "benchmark_options": {}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate sica-aime-2024 --route upstream --paper <paper>`.

- Pairwise Validator: AIME (`pairwise-validator-aime`; AIME)
- ShinkaEvolve: AIME 2024 scaffold design (`shinkaevolve-aime-2024-scaffold-design`; AIME 2024 scaffold design, AIME 2024 scaffold design)

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

- paper: https://arxiv.org/pdf/2504.15228 (Sections 4 and 4.1)
- repository: https://github.com/MaximeRobeyns/self_improving_coding_agent/tree/ed8275dca4d3c5dbf77229964351fe9b424797dc (base_agent/src/benchmarks/aime.py)
- paper: https://arxiv.org/pdf/2607.14408 (Section 5, Table 1 task inventory)
- paper: https://arxiv.org/pdf/2509.19349 (Section 3.2 and Appendix C.2)
- repository: https://github.com/SakanaAI/ShinkaEvolve/tree/9912af12d423504b8d580f4179fd15f5f88b8c50

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
