# TrackML complete-event track reconstruction

**Source collection:** [Particle physics: source-based research tasks](../../papers/science-particle.md)\
**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-particle-helical-track-reconstruction`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

assign_tracks(hits, cells, metadata) -> integer track ID for each hit. Input retains complete official TrackML events, source cells and detector geometry. Whole events split, no truth supplied. Score exact strict two-sided majority TrackML weighted score. No artificial helices or hit subsampling.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

assign_tracks(hits, cells, metadata) -> integer track ID for each hit. Input retains complete official TrackML events, source cells and detector geometry. Whole events split, no truth supplied. Score exact strict two-sided majority TrackML weighted score. No artificial helices or hit subsampling.

Parameters: `{"proposal_id": "P05"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `particle_physics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Associate detector hits with charged-particle trajectories in dense collider events.

Why it matters: Accurate, scalable track reconstruction supports particle identification and kinematic reconstruction and is itself the paper's target.

- [Performance of a geometric deep learning pipeline for HL-LHC particle tracking](https://link.springer.com/article/10.1140/epjc/s10052-021-09675-8): Main research objective: Develop and assess a scalable reconstruction method for complete TrackML detector events under high-luminosity conditions. Task connection: The current local task reconstructs whole TrackML events and uses weighted majority-hit matching. The shared scientific target is hit-to-track assignment; event selection, scoring, compute limits, and the candidate interface are local adaptations.

The source develops a solver for physical track reconstruction, so evidence does not depend on a dataset-release citation or the superseded synthetic-helix task.

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
- `file:data/physics-expansion/P05/manifest.json`
- `file:data/physics-expansion/P05/benchmark.npz`

## Sources

- paper: https://arxiv.org/abs/1904.06778v3 (The Tracking Machine Learning challenge: Accuracy phase; sections 1, 2.1-2.4 describe trajectory association, hit geometry, data and the official scoring problem.)
- benchmark: https://cds.cern.ch/record/2704180 (CERN Document Server: TrackML: a tracking Machine Learning challenge; primary CERN-hosted description of the challenge.)
- paper: https://arxiv.org/abs/1904.06778 (Scientific problem, assumptions and evaluation methodology: TrackML complete-event track reconstruction)
- archive: https://github.com/LAL/trackml-library (Complete event hits, cells, truth and detector geometry; strict majority score implementation.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Obtain full official TrackML events/cells/detector, preserve event boundaries; benchmark source files are not staged.
