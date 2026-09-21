# Satisfiable 3-CNF solving

**Paper:** Autonomous Code Evolution Meets NP-Completeness (https://arxiv.org/pdf/2509.07367)\
**Task id:** `reference-sat`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Return {"assignment": [booleans]}; score 1 iff every clause is satisfied. Literal k refers to assignment[abs(k)-1], negated when k < 0.

## Candidate interface

solve(instance) -> list of booleans (instance has n and clauses as signed 1-based literals). Score: fraction of satisfiable instances solved

Parameters: `{"n_instances": 10, "n_vars": 50, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2509.07367 (Problem family; original benchmark protocol is not claimed.)

## Limitations

- Portable reference implementation, not a reproduction of the original paper experiment.
- Generated deterministic instances are not the paper datasets. Scores are not comparable to published results.
