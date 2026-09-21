# SCiEL: lm-evaluation-harness GSM8K adapter

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-bench-lm-eval-gsm8k`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Answer GSM8K questions through the lm-eval.py adapter, which registers an 'openevolve' model in EleutherAI's lm-evaluation-harness and answers each prompt by running a short evolution over a text stub. The headline metric is GSM8K exact_match (strict-match) over the evaluated examples.

Benchmark named in the paper: SCiEL source example lm_eval. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api, network`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/lm_eval` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- This example is a CLI driver (lm-eval.py) that runs a prompt search against a model endpoint and grades with lm-eval; there is no evaluate() entry point.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `env:OPENROUTER_API_KEY`
- `network:huggingface datasets`
- `network:openrouter`
- `py:datasets`
- `py:lm_eval`
- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/lm_eval/evaluator_stub.py (evaluate and helper functions at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/lm_eval/initial_content_stub.txt (original baseline)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/lm_eval/README.md (source README)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- There is no candidate evaluator: evaluator_stub.py returns a constant, and scoring happens inside lm-evaluation-harness after model generation. No direct evaluator adapter is possible; the source command is recorded as a command-only interface.
- The source README states the early implementation has not been benchmarked and that metrics with --limit are not meaningful.
