# DROP

**Paper:** Automated Design of Agentic Systems (https://arxiv.org/pdf/2408.08435)\
**Paper:** AFlow: Automating Agentic Workflow Generation (https://arxiv.org/pdf/2410.10762)\
**Paper:** Gödel Agent: A Self-Referential Agent Framework for Recursively Self-Improvement (https://arxiv.org/pdf/2410.04444)\
**Paper:** Polymath: A Self-Optimizing Agent with Dynamic Hierarchical Workflow (https://arxiv.org/pdf/2508.02959)\
**Task id:** `adas-drop`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

DROP: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: DROP. Paper metric: DROP token F1.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "drop", "benchmark_options": {}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate adas-drop --route upstream --paper <paper>`.

- AFlow: DROP (`aflow-drop`; DROP, DROP)
- Gödel Agent: DROP (`g-del-agent-drop`; DROP, DROP)
- Polymath: DROP (`polymath-drop`; DROP, DROP)

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

- paper: https://arxiv.org/pdf/2408.08435 (Sections 4.1–4.2)
- repository: https://github.com/ShengranHu/ADAS/tree/2702bee8fefda42255efc5be9f60e3bd3db96ae4 (_drop/search.py)
- paper: https://arxiv.org/pdf/2410.10762 (Section 4.1)
- repository: https://github.com/FoundationAgents/AFlow/tree/3f457218fc716093fe53f6df8a5d5e6379d66346 (benchmarks/drop.py)
- paper: https://arxiv.org/pdf/2410.04444 (Section 4.1)
- repository: https://github.com/Arvid-pku/Godel_Agent/tree/bbb508796be31c7140cdfc7106efd830a1324242 (src/task_drop.py)
- paper: https://arxiv.org/pdf/2508.02959 (Experiments: Dataset and Evaluation Metrics)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
