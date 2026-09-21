# refnx contrast reflectometry inversion

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-refnx-contrast-inversion`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

infer_profile(training_contrasts, bounds, metadata) -> 32..4096 posterior rows [oxide thickness A, film thickness A, dry film SLD 1e-6/A^2, solvent fraction, roughness A, background]. Independent Parratt recursion with Nevot-Croce roughness and Gaussian Q-resolution predicts the wholly held-out contrast. Score posterior predictive normalized residual plus simulation-track CRPS. Source experimental contrasts are one physical sample, no cross-sample generalization claim.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

infer_profile(training_contrasts, bounds, metadata) -> 32..4096 posterior rows [oxide thickness A, film thickness A, dry film SLD 1e-6/A^2, solvent fraction, roughness A, background]. Independent Parratt recursion with Nevot-Croce roughness and Gaussian Q-resolution predicts the wholly held-out contrast. Score posterior predictive normalized residual plus simulation-track CRPS. Source experimental contrasts are one physical sample, no cross-sample generalization claim.

Parameters: `{"proposal_id": "P13"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `physics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer uncertain thin-film structure and composition from reflectometry measurements.

Why it matters: Resolving ambiguous structural inversions with calibrated posterior information is the paper's principal physical inference problem.

- [Fast and Reliable Probabilistic Reflectometry Inversion with Prior-Amortized Neural Posterior Estimation](https://arxiv.org/abs/2407.18648): Main research objective: Recover probabilistic thin-film structural information from ambiguous X-ray and neutron reflectometry data. Task connection: The local refnx task infers six layered-sample parameters and predicts a held-out contrast using three curves from one physical sample plus simulated training tracks. These contrast and parameter choices are a restricted local inverse problem, not the source paper's complete datasets or method.

The evidence directly targets reflectometry inversion; a reflectometry software paper alone would not establish the label.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independent SCIEL scientific adaptation. Required source packs never fall back to toy data. Fixture tests are distinct from source-data execution. See docs/PHYSICS_EXPANSION.md.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:data/physics-expansion/P13/manifest.json`
- `file:data/physics-expansion/P13/benchmark.npz`

## Sources

- paper: https://doi.org/10.1107/S1600576718017296 (Scientific problem, assumptions and evaluation methodology: refnx contrast reflectometry inversion)
- archive: https://github.com/refnx/refnx/tree/02b9bd11b439e8db8b319e6c25c7ee94b5033451/examples/global_fitting_motofit (Three measured contrasts e361r/e365r/e366r and source Motofit multilayer/global pilot files.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Run scripts/prepare_physics_expansion.py --refnx; experimental source is one sample with three contrasts.
