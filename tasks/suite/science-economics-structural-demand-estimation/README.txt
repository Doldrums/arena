# Economics: Structural differentiated-product demand estimation

**Source collection:** [Economics and quantitative finance: source-based research tasks](../../papers/science-economics_expansion.md)\
**Task id:** `science-economics-structural-demand-estimation`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Structural differentiated-product demand estimation with an explicit candidate API, independently recomputed objective and fixed model/data assumptions.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

estimate_demand(products, instrument_columns, model_spec, budget) -> sigma in[0,3] for a single random coefficient on horsepower/weight. Fixed linear controls 1,prices,hpwt,air,mpd,space; source BLP car data on two complete3-year market blocks. Fixed input-derived full-rank instrument span(QR removes exact redundancies),1-step GMM. Candidate9-point quadrature; independent15-point re-evaluation with1e-13 fixed-point tolerance. Minimize mean GMM objective per product, require share residual<1e-8. This is reduced structural-demand estimation, not full BLP replication.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `finance`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `finance`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate differentiated-product demand and substitution patterns in automobile markets.

Why it matters: Recovering structural demand and cost parameters from automobile-market data is an explicit primary objective of the BLP paper.

- [Automobile Prices in Market Equilibrium: Part I and II](https://www.nber.org/papers/w4264): Main research objective: Estimate structural demand and supply parameters for differentiated products and analyze the US automobile market. Task connection: The local task estimates automobile demand parameters using PyBLP-compatible GMM moments and an independent share calculation. Its demand specification and score isolate part of the original market-equilibrium problem, excluding the paper's full supply and policy analysis.

The original empirical demand paper supplies importance evidence; a PyBLP software paper alone is not used.

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
- `py:pandas`
- `py:pyblp`

## Sources

- paper: https://doi.org/10.1111/1756-2171.12352 (Conlon and Gortmaker: BLP random-coefficients GMM; bundled BLP automobile product data.)
- repository: https://github.com/jeffgortmaker/pyblp (Reference algorithms and source documentation; local evaluator is independently authored.)

## Limitations

- Bounded adaptation specified in the candidate contract; no claim to reproduce full-paper scores.
- Model/simulation scores do not establish empirical policy validity or market returns.
- Public fixed evaluation inputs support development only; freeze candidates and run new cases for generalization.
