# GSM8K

**Paper:** Promptbreeder: Self-Referential Self-Improvement via Prompt Evolution (https://arxiv.org/pdf/2309.16797)\
**Paper:** Automated Design of Agentic Systems (https://arxiv.org/pdf/2408.08435)\
**Paper:** AFlow: Automating Agentic Workflow Generation (https://arxiv.org/pdf/2410.10762)\
**Paper:** EvoFlow: Evolving Diverse Agentic Workflows On The Fly (https://arxiv.org/pdf/2502.07373)\
**Paper:** Polymath: A Self-Optimizing Agent with Dynamic Hierarchical Workflow (https://arxiv.org/pdf/2508.02959)\
**Task id:** `promptbreeder-gsm8k`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

GSM8K: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: GSM8K. Paper metric: accuracy.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "gsm8k", "benchmark_options": {}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate promptbreeder-gsm8k --route upstream --paper <paper>`.

- ADAS: GSM8K (`adas-gsm8k`; GSM8K, GSM8K)
- AFlow: GSM8K (`aflow-gsm8k`; GSM8K, GSM8K)
- EvoFlow: GSM8K (`evoflow-gsm8k`; GSM8K)
- Polymath: GSM8K (`polymath-gsm8k`; GSM8K, GSM8K)

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

- paper: https://arxiv.org/pdf/2309.16797 (Section 4 and Appendix I)
- paper: https://arxiv.org/pdf/2408.08435 (Section 4.3 and Appendix A)
- repository: https://github.com/ShengranHu/ADAS/tree/2702bee8fefda42255efc5be9f60e3bd3db96ae4 (_transfer_math/evaluation_gsm8k.py)
- paper: https://arxiv.org/pdf/2410.10762 (Section 4.1)
- repository: https://github.com/FoundationAgents/AFlow/tree/3f457218fc716093fe53f6df8a5d5e6379d66346 (benchmarks/gsm8k.py)
- paper: https://arxiv.org/pdf/2502.07373 (Section 4.1 and Appendix G.1)
- paper: https://arxiv.org/pdf/2508.02959 (Experiments: Dataset and Evaluation Metrics)

## Limitations

- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
