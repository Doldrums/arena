# BBH multistep_arithmetic_two

**Paper:** EvoPrompt: Connecting LLMs with Evolutionary Algorithms Yields Powerful Prompt Optimizers (https://arxiv.org/pdf/2309.08532)\
**Task id:** `evoprompt-bbh-multistep-arithmetic-two`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

BBH multistep_arithmetic_two task evaluated in EvoPrompt: Connecting LLMs with Evolutionary Algorithms Yields Powerful Prompt Optimizers.

Benchmark named in the paper: BIG-Bench Hard. Paper metric: accuracy.

## Candidate interface

solve(question, llm) -> answer string; llm(prompt_or_messages, system=None, max_tokens=None) is a budgeted, cached OpenRouter client. Score: mean per-item accuracy (or F1) on a fixed seeded sample of the benchmark

Parameters: `{"benchmark": "bbh", "benchmark_options": {"task": "multistep_arithmetic_two"}, "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `prompt`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Model-driven evaluation: the score depends on the model (ARTASK_LLM_MODEL, default google/gemini-2.5-flash), the sample size (ARTASK_LLM_SAMPLES, default 10) and the per-evaluation budget (ARTASK_LLM_BUDGET_USD, default 0.25). Responses are cached under .cache/llm-cache.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:datasets`
- `env:OPENROUTER_API_KEY`
- `network:openrouter+huggingface`

## Sources

- paper: https://arxiv.org/pdf/2309.08532 (Appendix C.2, Tables 17-18)
- repository: https://github.com/beeevita/EvoPrompt/tree/94caff336555df99acc5c338c7930c40cc550ad9 (BBH/eval.py)

## Limitations

- BBH scripts exist under BBH/scripts after the README cd BBH. Actual blocking defect: BBH/args.py registers --content twice, raising argparse.ArgumentError before execution; observed locally with parse_args(). Remove the duplicate declaration in a documented modified checkout before running BBH.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
