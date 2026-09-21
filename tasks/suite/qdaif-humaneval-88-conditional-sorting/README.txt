# HumanEval 88 conditional sorting

**Paper:** Quality-Diversity through AI Feedback (https://arxiv.org/pdf/2310.13032)\
**Task id:** `qdaif-humaneval-88-conditional-sorting`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

HumanEval 88 conditional sorting: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: HumanEval 88 conditional sorting. Paper metric: quality-diversity score and test pass count.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "humaneval", "benchmark_options": {"task_id": "HumanEval/88"}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

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

- paper: https://arxiv.org/pdf/2310.13032 (Appendix A.20)
- repository: https://github.com/CarperAI/OpenELM/tree/c844e149e3f59fef546e0bc55f4e12e0f192feb9

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Companion qdaif_scripts_data repository links results data on Google Drive; no LICENSE file was found in that repository. It does not provide one verified end-to-end paper-task CLI.
- No SPDX license identification verified for https://github.com/qdaif/qdaif_scripts_data.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
