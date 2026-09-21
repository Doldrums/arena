# ReSocratic

**Paper:** Co-evolving Agent Architectures and Interpretable Reasoning for Automated Optimization (https://arxiv.org/pdf/2604.17708)\
**Task id:** `evoor-agent-resocratic`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

ReSocratic

Benchmark named in the paper: ReSocratic. Paper metric: optimization-model solution accuracy.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the ReSocratic benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:ReSocratic`

## Sources

- paper: https://arxiv.org/pdf/2604.17708 (Section IV and Table III)
- repository: https://github.com/EvoNexusX/2026HuangEvoORAgent/tree/1a255eaade3b325706ab9b2ad1e20f2aafae0a06

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- Paper-provided anonymous code URL https://anonymous.4open.science/r/pL8xY2mQ8rA5fC3vB7nK could not be read: web tool inaccessible; direct HTTPS connection reset. No downloadable artifact verified.
- Official EvoOR-Agent release pinned; the LLM configuration is anonymized in the release and per-dataset selection is internal to evaluate.py.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
