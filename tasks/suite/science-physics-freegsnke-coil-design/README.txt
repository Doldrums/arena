# FreeGSNKE tokamak coil design

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-freegsnke-coil-design`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

design_coils(machine, target_boundary, plasma_profile) -> eight bounded active-coil currents in A for the published Anamak geometry. Evaluator runs pinned FreeGSNKE static equilibrium at two grid resolutions, checks nonlinear Grad-Shafranov residual, closed-plasma topology and current bounds, then scores boundary/axis mismatch. Targets/profile cases generated from the specified source model and saved with numerical reference checks. No physical reactor claim.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

design_coils(machine, target_boundary, plasma_profile) -> eight bounded active-coil currents in A for the published Anamak geometry. Evaluator runs pinned FreeGSNKE static equilibrium at two grid resolutions, checks nonlinear Grad-Shafranov residual, closed-plasma topology and current bounds, then scores boundary/axis mismatch. Targets/profile cases generated from the specified source model and saved with numerical reference checks. No physical reactor claim.

Parameters: `{"proposal_id": "P10"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `physics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Choose tokamak poloidal-field coil settings that produce a desired plasma equilibrium and shape.

Why it matters: Electromagnetic design capable of producing a target plasma geometry is the substantive fusion-engineering problem addressed by the paper.

- [Electromagnetic System Conceptual Design for a Negative Triangularity Tokamak](https://arxiv.org/abs/2501.14682): Main research objective: Design and assess an electromagnetic coil system capable of supporting the target equilibrium of a proposed tokamak. Task connection: The local task chooses eight bounded currents for an idealized Anamak geometry using FreeGSNKE static equilibrium checks. The paper studies another device and equilibrium code, with additional engineering considerations; the task is a limited coil-setting problem, not a reactor design validation.

The paper directly pursues magnetic-equilibrium design. A solver-software release is not used as the sole evidence.

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
- `file:data/physics-expansion/P10/manifest.json`
- `file:data/physics-expansion/P10/benchmark.npz`

## Sources

- paper: https://doi.org/10.1063/5.0188467 (Scientific problem, assumptions and evaluation methodology: FreeGSNKE tokamak coil design)
- repository: https://github.com/FusionComputingLab/freegsnke/tree/d755538c0f849e46f0e2407c0dad535eb9a1e228 (Version 3.1.0 example07a Anamak geometry and Lao85 profiles, static inverse and forward solves.)
- paper: https://arxiv.org/abs/2501.14682 (Uses equilibrium modeling to design bounded poloidal-coil currents and configurations that realize target plasma geometries. The local Anamak/FreeGSNKE static inverse problem uses different geometry and does not reproduce the paper's proposed reactor.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Run scripts/prepare_physics_expansion.py --coils with freegsnke==3.1.0 and NumPy<2.5.
