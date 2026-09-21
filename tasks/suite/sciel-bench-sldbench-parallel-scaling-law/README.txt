# SCiEL: SLDBench parallel scaling law

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-bench-sldbench-parallel-scaling-law`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Discover a symbolic scaling law and a parameter-fitting routine for SLDBench task parallel_scaling_law. Loss as a function of model size and inference parallelism degree. Programs are fitted on smaller-scale training groups and scored on held-out larger-scale test groups by combined_score = 1/(1+NMSE).

Benchmark named in the paper: SCiEL source example sldbench. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `discovery` (tier 1); artifact `equation`, domain `machine_learning`, data `real_measurements`, verification `exact`, reference `none`, resources `network`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/sldbench` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- One SCiEL example directory serves all sldbench tasks; EVAL_TASK_NAME selects this task (problem.json entry.env). The first evaluation downloads the pkuHaowei/sldbench Hugging Face dataset.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `network:huggingface pkuHaowei/sldbench`
- `py:datasets`
- `py:numpy`
- `py:scipy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/sldbench/evaluator.py (evaluate and helper functions at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/sldbench/init_program.py (original baseline)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/sldbench/README.md (source README)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The task YAML configurations referenced by the source README (examples/sldbench/configs/) are absent at the pinned commit; only the shared evaluator, seed and data loader are pinned.
- The Hugging Face dataset revision is selected by the upstream loader at run time; results can drift if the hub dataset changes.
