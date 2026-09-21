# Climate dynamics: partial-observation Lorenz-96 assimilation

**Source collection:** [Climate dynamics: source-based research tasks](../../papers/science-climate.md)\
**Task id:** `science-climate-lorenz96-assimilation`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Design an ensemble analysis update that reconstructs an evolving twenty-variable chaotic state from noisy observations of half its coordinates. The evaluator propagates the ensemble and compares each updated ensemble mean with independent high-accuracy reference trajectories.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

analyze(ensemble, observations, observed_indices, observation_variance) -> updated ensemble with the same (16,20) shape. Lorenz-96 dx_i/dt=(x_(i+1)-x_(i-2))*x_(i-1)-x_i+F with periodic indices, nondimensional units. Evaluator propagates each member by RK4 at dt=0.01 for five steps between updates, then observes even-indexed states with independent N(0,0.49) noise. Three runs F=6,8,10, seeds=181,283,389; 40 updates each. Score is pooled analysis-mean RMSE against independent DOP853 truth over all states and cycles. Output must be finite and within [-100,100]. Use assimilation_case with seeds=41,53,67 for development; no truth or future observations are provided to analyze.

Parameters: `{"cycles": 40}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `climate_dynamics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Reconstruct the hidden state of a reduced chaotic Lorenz-96 system from partial noisy observations.

Why it matters: Data assimilation has substantive geoscience uses, but an arbitrary reduced chaotic test does not inherit those uses automatically.


The cited paper combines ensemble Kalman filtering and reservoir computing and uses Lorenz-96 as a method demonstration. The local twenty-variable synthetic twin experiment is still a methodological testbed, with no inspected primary paper pursuing its exact state reconstruction as a substantive scientific or real-world question. No qualifying primary-goal evidence is established for this local task in this review; this is not a finding that the broader subject is unimportant.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Reduced deterministic Lorenz-96 twin experiment inspired by Tomizawa and Sawada (2021), Section 2. Local choices: 20 states, 16 members, perfect-model forcing, partial observations, short horizon and deterministic initial seeds. No reservoir computer is required. This is neither real weather nor a reproduction of the paper's scores. All evaluation seeds are public; use new seeds after freezing a candidate to assess generalization.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://gmd.copernicus.org/articles/14/5623/2021/ (Tomizawa and Sawada (2021), Combining ensemble Kalman filter and reservoir computing to predict spatiotemporal chaotic systems; Section 2.1 Eq. (1) Lorenz-96 dynamics and Section 2.2 ensemble data assimilation.)

## Limitations

- Synthetic deterministic twin experiments, not weather observations or the paper's reservoir-computing results.
- Local reduced dimensions, seeds, observation noise, spin-up, perfect-model forcing and short duration are documented in the contract. Longer-horizon stability and forecast skill are not established.
- All evaluation seeds are public. Use fresh seeds and forcing regimes after freezing the candidate for a generalization claim.
