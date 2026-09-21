# ARC-AGI-2

**Paper:** Harnessing Agentic Evolution (https://arxiv.org/pdf/2605.13821)\
**Paper:** AdaEvolve: Adaptive LLM Driven Zeroth-Order Optimization (https://arxiv.org/pdf/2602.20133)\
**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Task id:** `aevo-arc-agi-2`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

ARC-AGI-2

Benchmark named in the paper: ARC-AGI-2. Paper metric: exact task accuracy.

## Candidate interface

solve(task, llm) -> list of output grids, one per test input; task = {'train': [{'input','output'}], 'test': [{'input'}]}. Score: fraction of test grids reproduced exactly on a seeded sample of public evaluation tasks

Parameters: `{"version": 2, "split": "evaluation", "seed": 0}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `language`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate aevo-arc-agi-2 --route upstream --paper <paper>`.

- AdaEvolve: ARC-AGI-2 (`adaevolve-arc-agi-2`; ARC-AGI-2, 120 reasoning instances)
- EvoX: ARC-AGI-2 (`evox-arc-agi-2`; ARC-AGI-2, 120 reasoning instances)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Public ARC-AGI data (GitHub) converted to the Kaggle layout; the model, sample size and budget follow the llm family environment variables.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `env:OPENROUTER_API_KEY`
- `network:openrouter`
- `file:data/arc-prize-2025/arc-agi_evaluation_challenges.json`

## Sources

- paper: https://arxiv.org/pdf/2605.13821 (Section 5.1; Appendix C.1)
- paper: https://arxiv.org/pdf/2602.20133 (Experimental evaluation and additional-results appendix)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0 (benchmarks/arc_benchmark)
- paper: https://arxiv.org/pdf/2602.23413 (Experimental evaluation and additional-results appendix)

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- Paper cites Anthropic original_performance_takehome commit 5452f74; this is a simulated VLIW SIMD optimization problem, not a GPU kernel benchmark.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
