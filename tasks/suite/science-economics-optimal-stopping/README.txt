# Economics: Bermudan exercise-policy research

**Source collection:** [Economics and quantitative finance: source-based research tasks](../../papers/science-economics_expansion.md)\
**Task id:** `science-economics-optimal-stopping`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Bermudan exercise-policy research with an explicit candidate API, independently recomputed objective and fixed model/data assumptions.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit_exercise_policy(training_paths, contract) -> object with exercise(current_state,time) returning a boolean vector. Bermudan put on risk-neutral GBM,12monthly exercise dates(no time0exercise),4096training paths and8192independent evaluation paths per contract. Spot90/100/110,K100,r.05,sigma.2,T1. Maximize mean discounted payoff; antithetic-pair standard error and calendar-matched1200step binomial-tree reference are diagnostics. Candidate receives current states only during scoring, never future evaluation states.

## Labels

Scientific contribution: `method` (tier 2); artifact `policy`, domain `finance`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `finance`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine optimal exercise policies and values for options with early-exercise opportunities.

Why it matters: Valuing and optimally exercising American-style options is the central financial-mathematics problem in the source.

- [Valuing American Options by Simulation: A Simple Least-Squares Approach](https://doi.org/10.1093/rfs/14.1.113): Main research objective: Estimate continuation values by simulation to value and exercise American-style options. Task connection: The local task learns exercise policies for specified Bermudan models and checks them against independent discrete-tree calculations. Its finite exercise grid, path budgets, and models are restricted adaptations, not a reproduction of all published derivative examples.

The evidence directly treats the optimal-stopping and valuation problem, rather than using an option model only to showcase a generic agent.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Candidate outputs are independently re-evaluated. Baselines may call named public numerical helpers, but cannot supply their own objective. These bounded research-model adaptations do not establish empirical economic predictions or trading returns.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://escholarship.org/uc/item/43n1k4jb (Longstaff and Schwartz least-squares Monte Carlo; independent discrete-calendar tree reference.)
- repository: https://github.com/lballabio/QuantLib (Reference algorithms and source documentation; local evaluator is independently authored.)

## Limitations

- Bounded adaptation specified in the candidate contract; no claim to reproduce full-paper scores.
- Model/simulation scores do not establish empirical policy validity or market returns.
- Public fixed evaluation inputs support development only; freeze candidates and run new cases for generalization.
