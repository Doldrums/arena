# Economics: Heterogeneous-agent macroeconomic transitions

**Source collection:** [Economics and quantitative finance: source-based research tasks](../../papers/science-economics_expansion.md)\
**Task id:** `science-economics-macroeconomic-transitions`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Heterogeneous-agent macroeconomic transitions with an explicit candidate API, independently recomputed objective and fixed model/data assumptions.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

solve_transition(model, steady_state, aggregate_shock) -> length40 capital DEVIATIONS from steady state. Fixed sequence-jacobian Krusell-Smith source example (2 income states,10 asset nodes);24period productivity shocks plus16zero periods; household continuation uses fixed terminal steady-state value. Independently recompute nonlinear household/distribution/market paths. Minimize mean maximum asset-market residual / steady-state capital; check probability mass, positive consumption and feasible assets. Source household optimizer is fixed; candidate evolves equilibrium-path solution.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `finance`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `finance`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Solve aggregate transition paths in heterogeneous-household economies after economic shocks.

Why it matters: Computing and estimating general-equilibrium responses in heterogeneous-agent macroeconomics is the paper's central domain-specific target.

- [Using the Sequence-Space Jacobian to Solve and Estimate Heterogeneous-Agent Models](https://www.nber.org/papers/w26123): Main research objective: Solve and estimate heterogeneous-agent equilibrium models, including impulse responses and nonlinear transition paths. Task connection: The local task solves Krusell-Smith transition paths through market-clearing residuals under bounded shocks and horizons. It restricts the models and inference goals studied in the paper and does not reproduce its wider estimation exercises.

The method is designed to solve a specific economic-equilibrium problem, rather than presenting a general optimizer benchmark or a software release alone.

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
- `py:numba`
- `py:sequence_jacobian`

## Sources

- paper: https://doi.org/10.3982/ECTA17434 (Auclert et al.: sequence-space equilibrium; pinned package examples/krusell_smith.py.)
- repository: https://github.com/shade-econ/sequence-jacobian (Reference algorithms and source documentation; local evaluator is independently authored.)

## Limitations

- Bounded adaptation specified in the candidate contract; no claim to reproduce full-paper scores.
- Model/simulation scores do not establish empirical policy validity or market returns.
- Public fixed evaluation inputs support development only; freeze candidates and run new cases for generalization.
