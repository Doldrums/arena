# Terminal-Bench

**Paper:** Harnessing Agentic Evolution (https://arxiv.org/pdf/2605.13821)\
**Task id:** `aevo-terminal-bench`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Terminal-Bench

Benchmark named in the paper: Terminal-Bench. Paper metric: task success rate.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `software_engineering`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are LLM agents scored inside the Terminal-Bench environment (tools, web, games or code sandboxes); the environment and model access are external.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `environment:Terminal-Bench`

## Sources

- paper: https://arxiv.org/pdf/2605.13821 (Section 5.1; Appendix C.1)

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- Paper cites Anthropic original_performance_takehome commit 5452f74; this is a simulated VLIW SIMD optimization problem, not a GPU kernel benchmark.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
