# ArXivMath

**Paper:** Meta-Harness: End-to-End Optimization of Model Harnesses (https://arxiv.org/pdf/2603.28052)\
**Task id:** `meta-harness-arxivmath`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

ArXivMath task evaluated in Meta-Harness: End-to-End Optimization of Model Harnesses.

Benchmark named in the paper: ArXivMath. Paper metric: answer/proof accuracy.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `none`, reference `none`, resources `model_api, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Candidates are prompts, agent scaffolds or workflows whose fitness is measured by querying a language model on the ArXivMath benchmark. The suite embeds neither model calls nor the benchmark data.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `service:llm_api`
- `env:OPENROUTER_API_KEY`
- `dataset:ArXivMath`

## Sources

- paper: https://arxiv.org/pdf/2603.28052 (Section 4.2; 200 combined held-out problems)
- repository: https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact/tree/57fefdb2ff84af3fd81b69d67814acbe69bd0743

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
