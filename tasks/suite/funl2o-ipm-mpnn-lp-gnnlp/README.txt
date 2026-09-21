# IPM-MPNN LP GNNLP

**Paper:** FunL2O: LLM-Guided Feature Function Design for Learning to Optimize (https://arxiv.org/pdf/2607.27389)\
**Task id:** `funl2o-ipm-mpnn-lp-gnnlp`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

IPM-MPNN LP GNNLP

## Candidate interface

solve(problem, time_limit) -> x: a length-problem['n'] vector for the instance dict (kind, form in {qp, qcqp, socp, lp, milp}, arrays Q, p, A, b, G, h, lb, ub, and H/g/r, cones, c, A_ub, b_ub, A_eq, b_eq, integer as applicable; nonconvex instances add sum(sin(x)), nonsmooth ones add 0.5*||x||_1 to the objective). l2o.objective(problem, x), l2o.violation(problem, x) and l2o.scipy_constraints(problem) are available. Score: mean over five seeded instances of the relative optimality gap against an independent reference (Clarabel / HiGHS / multistart SLSQP); infeasible (violation > 1e-4), non-finite or over-time solutions count as gap 1. Lower is better.

Parameters: `{"kind": "generic_lp", "time_limit": 5.0}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `continuous_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Local instances of the generic lp family stand in for the paper's ipm mpnn lp gnnlp dataset.
- Local instances in the mathematical form of the paper's families (DC3 and FSNet QP/QCQP/SOCP, IPM-MPNN/PDHG-Net/pivot/basis LP families, predict-and-search and backdoor-branching MILPs) with reduced sizes; the paper's datasets, learned models and CPLEX are not used. References: cvxpy with Clarabel for convex problems, HiGHS for LP/MILP, best-of-8 SLSQP starts for nonconvex problems (best found, not proven optimal).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `py:cvxpy`

## Sources

- paper: https://arxiv.org/pdf/2607.27389 (Table 2 Panel A)

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
