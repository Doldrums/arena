# TDLMC time-delay distance posterior

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-tdlmc-distance-posterior`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

infer_distance(image, psf, time_delays, kinematics, metadata) -> 32..4096 joint physical posterior samples; first column time-delay distance Mpc, others named bounded lens/source nuisances. Metadata includes evaluator-owned lenstronomy forward callable and budget. TDLMC Rungs 1 or 2 whole systems only. Relative distance CRPS plus independent image/delay/dynamical forward-likelihood penalty; bias, interval width and coverage reported.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

infer_distance(image, psf, time_delays, kinematics, metadata) -> 32..4096 joint physical posterior samples; first column time-delay distance Mpc, others named bounded lens/source nuisances. Metadata includes evaluator-owned lenstronomy forward callable and budget. TDLMC Rungs 1 or 2 whole systems only. Relative distance CRPS plus independent image/delay/dynamical forward-likelihood penalty; bias, interval width and coverage reported.

Parameters: `{"proposal_id": "P07"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `cosmology_and_astrophysics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer time-delay distances from strongly lensed quasars to constrain the cosmic expansion rate.

Why it matters: Lensing distances and the resulting cosmological constraints are the primary scientific measurements in H0LiCOW XIII.

- [H0LiCOW XIII. A 2.4% measurement of H0 from lensed quasars: 5.3σ tension between early and late-Universe probes](https://arxiv.org/abs/1907.04869): Main research objective: Measure the Hubble constant and constrain cosmology using time-delay distances from gravitationally lensed quasars. Task connection: The local TDLMC task infers a distance posterior from simulated imaging, delays, PSFs, and kinematics. It isolates a lens-inference subproblem; its likelihood assumptions and posterior score do not reproduce the six-quasar observational analysis or its cosmological conclusions.

The evidence directly studies the physical quantity estimated by the task; a time-delay challenge announcement alone is insufficient.

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
- `file:../../.cache/physics-env/bin/python`
- `file:data/physics-expansion/P07/manifest.json`
- `file:data/physics-expansion/P07/benchmark.npz`

## Sources

- paper: https://arxiv.org/abs/2006.08619 (Scientific problem, assumptions and evaluation methodology: TDLMC time-delay distance posterior)
- archive: https://tdlmc.github.io/download.html (Rung 1 or 2 blinded images, PSF, delays, kinematics and open-box distances; omit Rung 3.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Curate Rung 1/2 source cases and model/kinematics priors, install lenstronomy and verify forward rendering against source.
