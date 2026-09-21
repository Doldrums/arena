# SCiEL: ARC-AGI evaluation task 0 (arc-prize-2025)

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-bench-arc-agi-evaluation-task-0`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Write two grid-transformation attempts (transform_grid_attempt_1/2 over numpy arrays) for one ARC-AGI task selected by index from the arc-prize-2025 challenge file. The pinned evaluator scores pass@2 accuracy over the task's training pairs; the source README's default is evaluation-set index 0 (task 0934a4d8).

Benchmark named in the paper: SCiEL source example arc_benchmark. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `program`, domain `language`, data `public_benchmark`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/arc_benchmark` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- Needs the ARC Prize 2025 JSON files under suite/_lib/data/arc-prize-2025 (Kaggle download); DATA_ROOT/ARC_TASK_FILE/TASK_NUM select the task.
- Imports openevolve.evaluation_result; suite/_lib/openevolve is a verbatim shim of that module.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `file:data/arc-prize-2025/arc-agi_evaluation_challenges.json`
- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/arc_benchmark/evaluator.py (evaluate and helper functions at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/arc_benchmark/initial_program.py (original baseline)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/arc_benchmark/README.md (source README)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The score is pass@2 on the task's training pairs; held-out test-pair scoring uses the separate post_evolution_eval.py script and the solutions file.
- One package represents the parameterized example; other task indices and splits are selected through the documented environment variables rather than enumerated as packages.
