# DevEval real-world function completion

**Paper:** CoCoEvo: Co-Evolution of Programs and Test Cases to Enhance Code Generation (https://arxiv.org/pdf/2502.10802)\
**Task id:** `cocoevo-deveval-real-world-function-completion`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

DevEval real-world function completion task evaluated in CoCoEvo: Co-Evolution of Programs and Test Cases to Enhance Code Generation.

Benchmark named in the paper: Selected DevEval problems. Paper metric: pass@1.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the Selected DevEval problems benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:Selected DevEval problems`

## Sources

- paper: https://arxiv.org/pdf/2502.10802 (Section V-H)
- repository: https://github.com/lbaf23/llm-cocoevo/tree/504355b568b2a0cbd4054783c80bac9c76a4de6d

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- Official CoCoEvo release pinned; program/test co-evolution needs a code model endpoint and the separately downloaded contest/real-world datasets.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
