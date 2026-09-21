# SCiEL: prompt optimization on ifeval

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-bench-prompt-optimization-ifeval`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Evolve a text prompt for the task model on the google/IFEval dataset (train split). Instruction-following with multiple verifiable constraints per prompt; binary success. The pinned evaluator sends each sampled example to the configured task model and reports accuracy as combined_score.

Benchmark named in the paper: SCiEL source example llm_prompt_optimization. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api, network`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/llm_prompt_optimization` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- The candidate is a prompt text file; OPENEVOLVE_PROMPT selects the dataset configuration. Every evaluation queries the task model through an OpenAI-compatible endpoint; the copied config.yaml is re-pointed at OpenRouter (google/gemini-2.5-flash) and OPENAI_API_KEY is taken from OPENROUTER_API_KEY. The dataset YAML keeps the upstream sample size (up to 200 items per evaluation).

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
- `py:numpy`
- `py:openai`
- `py:tqdm`
- `py:yaml`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/llm_prompt_optimization/evaluator.py (evaluate and helper functions at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/llm_prompt_optimization/ifeval_prompt.txt (original baseline)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/llm_prompt_optimization/README.md (source README)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- No direct candidate evaluator adapter is registered: the pinned task evaluator itself performs model calls, which the no-model-call seed-check contract of this repository excludes. The original search and baseline commands are recorded instead.
- Task-model choice, endpoint and sampling temperature are set in the source config.yaml; scores are not comparable across models or endpoints.
