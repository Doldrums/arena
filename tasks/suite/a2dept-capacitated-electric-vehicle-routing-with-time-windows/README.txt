# Capacitated Electric Vehicle Routing with Time Windows

**Paper:** A2DEPT: Large Language Model-Driven Automated Algorithm Design via Evolutionary Program Trees (https://arxiv.org/pdf/2604.24043)\
**Task id:** `a2dept-capacitated-electric-vehicle-routing-with-time-windows`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Capacitated Electric Vehicle Routing with Time Windows

Benchmark named in the paper: FrontierCO and high-constraint extensions. Paper metric: mean normalized optimality gap.

## Candidate interface

plan(instance) -> list of routes (lists of node ids; depot 0 implicit; charging stations may appear repeatedly). Vehicles have capacity, battery (1 unit per distance) and must respect customer time windows. Score: mean total distance

Parameters: `{"n_instances": 3, "n_customers": 25, "n_stations": 4, "seed": 0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Route battery-electric delivery vehicles subject to customer time windows, load limits and recharging requirements.

Why it matters: Feasible routing under battery and service constraints is necessary for practical electric freight operations. The task studies a simplified operational planning problem with an independently researched objective.

- [The Electric Vehicle-Routing Problem with Time Windows and Recharging Stations](https://doi.org/10.1287/trsc.2013.0490): Main research objective: Optimize feasible electric-vehicle delivery routes while respecting time windows and battery charging constraints. Task connection: Schneider, Stenger and Goeke formulate and solve E-VRPTW with recharging stations. The local package uses generated instances and its own evaluator, rather than claiming replication of their complete instance set.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

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

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
