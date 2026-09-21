# HotPotQA

**Paper:** Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs (https://arxiv.org/pdf/2406.11695)\
**Paper:** AFlow: Automating Agentic Workflow Generation (https://arxiv.org/pdf/2410.10762)\
**Paper:** GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning (https://arxiv.org/pdf/2507.19457)\
**Paper:** Reward-Free Evolving Agents via Pairwise Validator (https://arxiv.org/pdf/2607.14408)\
**Paper:** Polymath: A Self-Optimizing Agent with Dynamic Hierarchical Workflow (https://arxiv.org/pdf/2508.02959)\
**Task id:** `mipro-hotpotqa`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

HotPotQA: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: HotPotQA. Paper metric: exact match.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "hotpotqa", "benchmark_options": {}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate mipro-hotpotqa --route upstream --paper <paper>`.

- AFlow: HotpotQA (`aflow-hotpotqa`; HotpotQA, HotpotQA)
- GEPA: HotpotQA (`gepa-hotpotqa`; HotpotQA)
- MIPRO: HotPotQA Conditional (`mipro-hotpotqa-conditional`; HotPotQA Conditional, HotPotQA Conditional)
- Pairwise Validator: HotpotQA (`pairwise-validator-hotpotqa`; HotpotQA)
- Polymath: HotpotQA (`polymath-hotpotqa`; HotpotQA, HotpotQA)

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

- paper: https://arxiv.org/pdf/2406.11695 (Table 1 and Appendices A/E)
- repository: https://github.com/stanfordnlp/dspy/tree/40a6e168914a7b81a78b1a081d93f26de18c8d0d
- paper: https://arxiv.org/pdf/2410.10762 (Section 4.1)
- repository: https://github.com/FoundationAgents/AFlow/tree/3f457218fc716093fe53f6df8a5d5e6379d66346 (benchmarks/hotpotqa.py)
- paper: https://arxiv.org/pdf/2507.19457 (Section 4 evaluation and benchmark appendix)
- repository: https://github.com/gepa-ai/gepa-artifact/tree/cbefbc1aa0f43dd39874ec4bf42211365dbda42e (gepa_artifact/benchmarks/hotpotQA)
- paper: https://arxiv.org/pdf/2607.14408 (Section 5, Table 1 task inventory)
- paper: https://arxiv.org/pdf/2508.02959 (Experiments: Dataset and Evaluation Metrics)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Current DSPy repository has MIPROv2 optimizer but the seven original 2024 benchmark drivers were not located in the inspected tree; API library availability alone does not make original tasks executable.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
