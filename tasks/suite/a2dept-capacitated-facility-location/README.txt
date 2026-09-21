# Capacitated Facility Location

**Paper:** A2DEPT: Large Language Model-Driven Automated Algorithm Design via Evolutionary Program Trees (https://arxiv.org/pdf/2604.24043)\
**Paper:** FunL2O: LLM-Guided Feature Function Design for Learning to Optimize (https://arxiv.org/pdf/2607.27389)\
**Task id:** `a2dept-capacitated-facility-location`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Capacitated Facility Location

Benchmark named in the paper: FrontierCO and high-constraint extensions. Paper metric: mean normalized optimality gap.

## Candidate interface

assign(demands, capacities, open_cost, assign_cost[customer, facility]) -> facility index per customer respecting capacities. Score: mean total opening + assignment cost

Parameters: `{"n_instances": 5, "n_facilities": 20, "n_customers": 100, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate a2dept-capacitated-facility-location --route upstream --paper <paper>`.

- FunL2O: IPM-MPNN LP Facility location (`funl2o-ipm-mpnn-lp-facility-location`)

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

- paper: https://arxiv.org/pdf/2604.24043 (Section 4; Appendix D Table 5)
- paper: https://arxiv.org/pdf/2607.27389 (Table 2 Panel A)

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
