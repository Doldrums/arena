# SCiEL: AlgoTune complex eigenvectors

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-algotune-eigenvectors-complex`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Compute the required eigendecomposition of a complex matrix and maximize measured reference-relative speedup.

Benchmark named in the paper: SCiEL source example algotune/eigenvectors_complex. Paper metric: speedup_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `program`, domain `numerical_computing`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/algotune/eigenvectors_complex` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

- The SCiEL evaluator (kept verbatim as evaluator_sciel.py) expects an AlgoTune checkout at fixed paths; evaluator.py loads it with the byte-verified vendored subset in suite/_lib/vendor/algotune (see SOURCES.json) and injects TASK_REGISTRY, leaving the scoring code unchanged.
- Imports openevolve.evaluation_result; suite/_lib/openevolve is a verbatim shim of that module.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:orjson`
- `py:threadpoolctl`
- `py:yaml`
- `vendor:algotune`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/algotune/eigenvectors_complex/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/algotune/eigenvectors_complex/initial_program.py (original baseline)
- repository: https://github.com/oripress/AlgoTune/blob/dff9914c10800c7a031c9e8c3d4d1c8cd1b38906/AlgoTuneTasks/eigenvectors_complex/eigenvectors_complex.py (Recovered official task generator/solver dependency; immutable additional pin)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The evaluator checks candidate.Class().is_solution(), so candidate code controls the correctness predicate. SCiEL did not pin its external AlgoTune registry; this recovery supplies an explicit additional revision. Reported correctness and speedup do not provide independent verification.
- Timing includes Python thread dispatch and measures short numerical operations; noise and environment changes can dominate speedup.
- The upstream evaluator provides no independently trusted validity boolean; a finite returned score remains unverified.
