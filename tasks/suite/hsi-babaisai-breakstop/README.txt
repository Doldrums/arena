# BabaIsAI BreakStop

**Paper:** Hierarchical Self-Improvement: A Framework for Task-Specific Evolvable Agent Harnesses (https://arxiv.org/pdf/2608.08466)\
**Task id:** `hsi-babaisai-breakstop`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

BabaIsAI BreakStop

Benchmark named in the paper: BALROG. Paper metric: episode progress / task success.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `software_engineering`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are LLM agents scored inside the BALROG environment (tools, web, games or code sandboxes); the environment and model access are external.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `environment:BALROG`

## Sources

- paper: https://arxiv.org/pdf/2608.08466 (Section 4)
- repository: https://github.com/TailinZhou/hsi/tree/97a022b9a9c260c0498806fc9826ebf22e753ed9 (benchmark_config_goal/balrog_babaisai_breakstop/config.yaml)

## Limitations

- No root license was found in the inspected upstream tree; preserve upstream licensing conditions and do not assume redistribution rights.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
