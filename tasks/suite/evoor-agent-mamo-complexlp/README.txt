# MAMO ComplexLP

**Paper:** Co-evolving Agent Architectures and Interpretable Reasoning for Automated Optimization (https://arxiv.org/pdf/2604.17708)\
**Task id:** `evoor-agent-mamo-complexlp`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

MAMO ComplexLP

Benchmark named in the paper: MAMO ComplexLP. Paper metric: optimization-model solution accuracy.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "mamo_complex", "benchmark_options": {}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

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

- paper: https://arxiv.org/pdf/2604.17708 (Section IV and Table III)
- repository: https://github.com/EvoNexusX/2026HuangEvoORAgent/tree/1a255eaade3b325706ab9b2ad1e20f2aafae0a06

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- Paper-provided anonymous code URL https://anonymous.4open.science/r/pL8xY2mQ8rA5fC3vB7nK could not be read: web tool inaccessible; direct HTTPS connection reset. No downloadable artifact verified.
- Official EvoOR-Agent release pinned; the LLM configuration is anonymized in the release and per-dataset selection is internal to evaluate.py.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
