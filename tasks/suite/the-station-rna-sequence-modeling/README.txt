# RNA sequence modeling

**Paper:** The Station: An Open-World Environment for AI-Driven Discovery (https://arxiv.org/pdf/2511.06309)\
**Task id:** `the-station-rna-sequence-modeling`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

RNA sequence modeling: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: RNA sequence modeling. Paper metric: mean validation metric over seven datasets.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `discovery` (tier 1); artifact `program`, domain `natural_science`, data `real_measurements`, verification `none`, reference `none`, resources `gpu, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: The Station's research tasks need large scientific datasets (single-cell atlases, ZAPBench, RNA benchmarks) or RL training.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `dataset:RNA sequence modeling`
- `hardware:gpu`

## Sources

- paper: https://arxiv.org/pdf/2511.06309 (Sections 3.2–3.5 and Appendix B)
- repository: https://github.com/dualverse-ai/station/tree/782088e561998bf357d95a838a0566a8229425d9 (example/research_misc/rna/misc/eval.py)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
