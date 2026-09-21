# Terminal-Bench 2

**Paper:** Agentic Harness Engineering: Observability-Driven Automatic Evolution of Coding-Agent Harnesses (https://arxiv.org/pdf/2604.25850)\
**Task id:** `ahe-terminal-bench-2`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Terminal-Bench 2

Benchmark named in the paper: Terminal-Bench 2. Paper metric: pass rate.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `software_engineering`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are LLM agents scored inside the Terminal-Bench 2 environment (tools, web, games or code sandboxes); the environment and model access are external.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `environment:Terminal-Bench 2`

## Sources

- paper: https://arxiv.org/pdf/2604.25850 (Section 4; Appendix A)
- repository: https://github.com/china-qijizhifeng/agentic-harness-engineering/tree/8b2a55d97590363fe50c3cc6b5e833b020a4bb4c (configs/base.yaml)

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
