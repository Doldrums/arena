# Jailbreak

**Paper:** Automatic Prompt Optimization with “Gradient Descent” and Beam Search (https://arxiv.org/pdf/2305.03495)\
**Task id:** `protegi-jailbreak`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Jailbreak: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Jailbreak. Paper metric: F1.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the Jailbreak benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:Jailbreak`

## Sources

- paper: https://arxiv.org/pdf/2305.03495 (Section 4)
- repository: https://github.com/microsoft/LMOps/tree/6f53ef41c951de0962bbf27fe3f5819eabc8ce0e (prompt_optimization/main.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Code expects the API key in config.OPENAI_KEY, not the OPENAI_API_KEY environment variable, and hardcodes historical model names. No repository dependency manifest for this subproject was found.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
