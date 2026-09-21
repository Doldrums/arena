# Vet code-verification prompt evolution

**Paper:** LLM-based Evolution as a Universal Optimizer (Darwinian Evolver) (https://imbue.com/blog/2026-02-27-darwinian-evolver)\
**Task id:** `darwinian-evolver-vet-code-verification-prompt-evolution`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Vet code-verification prompt evolution

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the Vet code-verification prompt evolution benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:Vet code-verification prompt evolution`

## Sources

- paper: https://imbue.com/blog/2026-02-27-darwinian-evolver (Blog optimization use cases)
- repository: https://github.com/imbue-ai/darwinian_evolver/tree/7f12365d2059c47e29068a5a6f498a293148d2a9

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
