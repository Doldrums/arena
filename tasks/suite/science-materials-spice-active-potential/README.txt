# SPICE label-efficient molecular potentials

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-spice-active-potential`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

acquire(unlabeled_geometries, observations, budget)->unused indices; fit(observations)->object with potential(atomic_numbers, coordinates_angstrom)->(energy_ev, forces_ev_angstrom). Eight precomputed quantum-label queries from12 source acquisition geometries in the bounded pilot;14 evaluation geometries hold out entire ligand groups. Score force RMSE/(1 eV/Angstrom) + molecule-centered relative-energy RMSE/(1 eV) on source-group holdouts. Independent finite differences check force/energy consistency, rigid-motion symmetries, net force/torque; short evaluator-controlled trajectories check numerical stability. All units are explicit and a test fixture never substitutes for SPICE.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

acquire(unlabeled_geometries, observations, budget)->unused indices; fit(observations)->object with potential(atomic_numbers, coordinates_angstrom)->(energy_ev, forces_ev_angstrom). Eight precomputed quantum-label queries from12 source acquisition geometries in the bounded pilot;14 evaluation geometries hold out entire ligand groups. Score force RMSE/(1 eV/Angstrom) + molecule-centered relative-energy RMSE/(1 eV) on source-group holdouts. Independent finite differences check force/energy consistency, rigid-motion symmetries, net force/torque; short evaluator-controlled trajectories check numerical stability. All units are explicit and a test fixture never substitutes for SPICE.

Parameters: `{"proposal_id": "C10", "budget": 8, "data_sha256": "3f07257780621a13f47a7f1df2d78170979f6c3cb6e89c778777bdcbb917b5f5"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `model`, domain `natural_science`, data `public_benchmark`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `chemistry`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Learn molecular energies and forces with limited expensive quantum-chemical labels.

Why it matters: Accurate molecular potentials can make physically informed molecular simulation less costly.


SPICE is a dataset paper. The inspected active-learning ANI study (Less is more: sampling chemical space with active learning) pursues transferable molecular potentials, but the current eight-query pilot has only twelve acquisition and fourteen evaluation geometries. This review did not establish that this restricted pilot preserves that substantive research objective rather than primarily testing an acquisition interface; no transferable-potential result follows from the pilot. No qualifying primary-goal evidence is established for this local task in this review; this is not a finding that the broader subject is unimportant.

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
- `py:rdkit`
- `file:data/materials-expansion/C10/dataset.json`

## Sources

- paper: https://doi.org/10.1038/s41597-022-01882-6 (SPICE quantum chemistry dataset; energy/force target definitions and molecular coverage.)
- repository: https://github.com/openmm/spice-dataset (Official source generation scripts and units.)
- benchmark: https://zenodo.org/records/10975225 (Versioned SPICE quantum labels; conversion to eV/Angstrom and whole-molecule holdouts required.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Bounded eight-query interaction-complex pilot:12 training geometries and14 evaluation geometries, entire ligand groups held out. Not full SPICE training or leaderboard reproduction.
- Retrieved HDF5 ranges and normalized bundle are SHA256-pinned; full37.5GB source-file checksum was not verified. Unit conversions are verified against HDF5 units.
