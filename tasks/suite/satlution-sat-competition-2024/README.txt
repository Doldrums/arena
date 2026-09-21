# SAT Competition 2024

**Paper:** Autonomous Code Evolution Meets NP-Completeness (https://arxiv.org/pdf/2509.07367)\
**Task id:** `satlution-sat-competition-2024`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

SAT Competition 2024: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: SAT Competition 2024. Paper metric: solved instances and PAR-2.

## Candidate interface

solve(instance) -> list of booleans (instance has n and clauses as signed 1-based literals). Score: fraction of satisfiable instances solved

Parameters: `{"n_instances": 6, "n_vars": 150, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate satlution-sat-competition-2024 --route upstream --paper <paper>`.

- SATLUTION: SAT Competition 2025 (`satlution-sat-competition-2025`; SAT Competition 2025, SAT Competition 2025)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- SATLUTION evolves a C/C++ CDCL solver on SAT Competition instances; this suite evaluates a Python solver contract on generated satisfiable 3-CNF instances.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2509.07367 (Experimental Setup)

## Limitations

- No official runnable repository was verified from the paper/project sources examined.
- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
