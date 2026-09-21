# Economics: Incentive-compatible finite auction design

**Source collection:** [Economics and quantitative finance: source-based research tasks](../../papers/science-economics_expansion.md)\
**Task id:** `science-economics-finite-auction-design`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Incentive-compatible finite auction design with an explicit candidate API, independently recomputed objective and fixed model/data assumptions.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct_auction(distribution_spec, support, constraints) -> {allocations:(16,2),payments:(16,)}. One additive bidder,two goods,each value in{0,1,2,3},three fixed distributions. Every allowed report is enumerated; require feasible probabilities, nonnegative payments, individual rationality and regret<=1e-8. Maximize expected revenue normalized by an independently solved finite-support mechanism LP. Truthfulness holds only on the declared report/value support.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `finance`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `finance`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Design revenue-maximizing auctions subject to incentive-compatibility constraints.

Why it matters: Optimal multi-item mechanism design is the primary economics problem addressed in the paper.

- [Optimal Auctions through Deep Learning](https://proceedings.mlr.press/v97/duetting19a.html): Main research objective: Find high-revenue incentive-compatible auctions, including settings where analytical optimal mechanisms are unknown. Task connection: The local task restricts auctions to finite supports and checks deviations exhaustively against an LP reference. These exact finite constraints and distributions differ from the paper's neural mechanisms and approximate training procedure.

The paper attempts to solve a substantive auction-design problem; deep learning is a solution method, not the task's sole justification.

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

- paper: https://proceedings.mlr.press/v97/duetting19a.html (RegretNet research objective; local finite-support mechanism replaces approximate sampled regret with exhaustive deviations.)
- repository: https://github.com/saisrivatsan/deep-opt-auctions (Reference algorithms and source documentation; local evaluator is independently authored.)

## Limitations

- Bounded adaptation specified in the candidate contract; no claim to reproduce full-paper scores.
- Model/simulation scores do not establish empirical policy validity or market returns.
- Public fixed evaluation inputs support development only; freeze candidates and run new cases for generalization.
