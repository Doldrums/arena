# CaloChallenge photon shower generation

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-calochallenge-photon-showers`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

fit_showers(training) -> sampler(incident_energies, rng). Training contains showers, incident_energies and voxel geometry from official CaloChallenge Dataset 1 photons. Return nonnegative (event,voxel) deposits in MeV. Independent source-file events are held out. Score per-energy standardized Wasserstein of shower response, sparsity, layer fractions, centroids and widths. Classifier AUC and generation time are separate diagnostics. Compact CPU adaptation, not full challenge leaderboard.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit_showers(training) -> sampler(incident_energies, rng). Training contains showers, incident_energies and voxel geometry from official CaloChallenge Dataset 1 photons. Return nonnegative (event,voxel) deposits in MeV. Independent source-file events are held out. Score per-energy standardized Wasserstein of shower response, sparsity, layer fractions, centroids and widths. Classifier AUC and generation time are separate diagnostics. Compact CPU adaptation, not full challenge leaderboard.

Parameters: `{"proposal_id": "P04"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `particle_physics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Generate accurate conditional calorimeter showers at lower computational cost than detailed particle-transport simulation.

Why it matters: Fast, faithful detector-response simulation is the primary target of CaloFlow research.

- [CaloFlow: Fast and Accurate Generation of Calorimeter Showers with Normalizing Flows](https://arxiv.org/abs/2106.05285): Main research objective: Accelerate calorimeter shower simulation while retaining realistic shower distributions and correlations. Task connection: The local task generates nonnegative showers conditioned on photon energy using a CaloChallenge source dataset and a CPU-oriented feature-Wasserstein score. Those data, restrictions, and score do not reproduce the CaloFlow experiment.

This is a direct proposed solution to detector simulation, replacing reliance on the CaloChallenge benchmark paper alone.

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
- `py:sklearn`
- `file:data/physics-expansion/P04/manifest.json`
- `file:data/physics-expansion/P04/benchmark.npz`

## Sources

- paper: https://arxiv.org/abs/2410.21611 (Scientific problem, assumptions and evaluation methodology: CaloChallenge photon shower generation)
- archive: https://zenodo.org/records/8099322 (dataset_1_photons_1.hdf5 and dataset_1_photons_2.hdf5, independent training/reference files.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Run scripts/prepare_physics_expansion.py --calo.
