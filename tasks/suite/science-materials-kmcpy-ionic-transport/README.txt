# NASICON occupation-dependent transport with exact finite-state reference

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-kmcpy-ionic-transport`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

transport(lattice, occupancies, barrier_model, temperature_k, budget) -> exactly budget['events'] [waiting_time_seconds, directed_edge_index] pairs. For the pinned NASICON model, Na state is0 and vacancy1; Si/P framework states remain fixed. barrier_model['nasicon_lce'] supplies occupation-dependent decorated LCE sums, source fitted parameters, local environments and directed periodic hop vectors. Rates are nu*exp(-(E_KRA+direction*DeltaE_site/2)/(kBT)). Preserve particle identity, exclusion and unwrapped periodic displacement. Evaluator independently audits clocks/events and compares 1000-event mean tagged-ion MSD/(6 mean physical time) against exact propagation over1680 tagged states. Score candidate runtime*relative_standard_error^2 across64 replicas. This bounded source illustrative model does not establish bulk/asymptotic conductivity or a new validated material fit.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

transport(lattice, occupancies, barrier_model, temperature_k, budget) -> exactly budget['events'] [waiting_time_seconds, directed_edge_index] pairs. For the pinned NASICON model, Na state is0 and vacancy1; Si/P framework states remain fixed. barrier_model['nasicon_lce'] supplies occupation-dependent decorated LCE sums, source fitted parameters, local environments and directed periodic hop vectors. Rates are nu*exp(-(E_KRA+direction*DeltaE_site/2)/(kBT)). Preserve particle identity, exclusion and unwrapped periodic displacement. Evaluator independently audits clocks/events and compares 1000-event mean tagged-ion MSD/(6 mean physical time) against exact propagation over1680 tagged states. Score candidate runtime*relative_standard_error^2 across64 replicas. This bounded source illustrative model does not establish bulk/asymptotic conductivity or a new validated material fit.

Parameters: `{"proposal_id": "C11", "data_sha256": "2c04311021f4253b8766589d0dd6e5cb09d008d459e9803aab17c833db4d41b8"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `materials_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Predict sodium-ion motion in mixed-polyanion NASICON solid electrolytes.

Why it matters: Ion transport controls the conductivity of candidate solid-state battery electrolytes.

- [Fundamental investigations on the sodium-ion transport properties of mixed polyanion solid-state battery electrolytes](https://www.nature.com/articles/s41467-022-32190-7): Main research objective: Explain how Si/P polyanion composition controls Na-ion transport and identify favorable NASICON compositions using kinetic simulations and impedance measurements. Task connection: The paper studies the same Na1+xZr2SixP3-xO12 material family and occupation-dependent hopping physics. The local source illustrative model estimates finite-time tagged-ion motion on a tiny fixed lattice; it does not reproduce bulk conductivity, the composition survey or experimental validation.

This is a physical ion-transport investigation, replacing reliance on a kMCpy software citation. Support is for the transport-model subproblem, with finite-model limitations explicit.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independently implemented SCIEL adaptation. Source bundles are required except the specified PFHub and Cantera simulations; no generated replacement data. See docs/MATERIALS_EXPANSION.md for provenance, exact setup blockers and validation scope.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:data/materials-expansion/C11/dataset.json`

## Sources

- paper: https://caneparesearch.org/papers/deng-kmcpy/ (kMCpy framework for solid-state diffusion simulations.)
- repository: https://github.com/caneparesearch/kMCpy/tree/7761fdd2c0506763816d5b0b42226b224f60dc70 (Pinned NASICON model/events, example fitting_results and fitting_results_site, active-site encoding, primitive lattice; complete decorated LCE evaluation and exact local finite-event transport reference.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Pinned source2x1x1 NASICON illustrative LCE model, two vacancies and fixed Si framework. The author provides identical KRA/site fit coefficients, retained as published. This is not independent validation of those fitted coefficients.
- The score measures finite1000-event tagged-ion transport. Exact2000-event value is also reported to expose finite-horizon dependence; no bulk/asymptotic conductivity claim.
