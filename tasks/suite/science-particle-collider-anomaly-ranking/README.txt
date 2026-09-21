# LHCO control-region collider anomalies

**Source collection:** [Particle physics: source-based research tasks](../../papers/science-particle.md)\
**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-particle-collider-anomaly-ranking`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

fit(control_features) -> object with score(events). Input consists of pinned physics features derived from official LHCO Pythia/Delphes events; candidate never receives signal truth. Independent training, test and no-signal source event blocks. Score SIC at 5 percent background divided by one plus mass-sculpting chi-square. Report no-signal acceptance and AUROC; no discovery p value.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit(control_features) -> object with score(events). Input consists of pinned physics features derived from official LHCO Pythia/Delphes events; candidate never receives signal truth. Independent training, test and no-signal source event blocks. Score SIC at 5 percent background divided by one plus mass-sculpting chi-square. Report no-signal acceptance and AUROC; no discovery p value.

Parameters: `{"proposal_id": "P06"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `particle_physics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Identify possible new-physics resonances without requiring a specific signal model or sculpting a false mass peak.

Why it matters: Model-independent collider searches are the central physics-search objective of the cited anomaly-detection method.

- [Classifying anomalies through outer density estimation](https://doi.org/10.1103/PhysRevD.106.055006): Main research objective: Improve resonant anomaly searches through data-driven background estimation using sidebands. Task connection: The local task uses LHCO events, unlabeled control-region training, and significance improvement with a mass-sculpting penalty. Its fixed features and scoring are narrower than the published method and do not constitute an experimental discovery search.

The paper proposes a solution to a specific new-physics search problem, beyond documenting an anomaly benchmark.

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
- `file:data/physics-expansion/P06/manifest.json`
- `file:data/physics-expansion/P06/benchmark.npz`

## Sources

- paper: https://arxiv.org/abs/2101.08320 (The LHC Olympics 2020: A Community Challenge for Anomaly Detection in High Energy Physics; section 2 (challenge), section 3.2.2 and figure 9 (ROC and signal/background efficiencies).)
- benchmark: https://ep-news.web.cern.ch/machine-learning-ushers-new-paradigm-particle-searches-lhc (CERN EP newsletter, LHC Olympics 2020 Challenge: reference background, predominantly background black boxes, and localized overdensity searches.)
- paper: https://arxiv.org/abs/2101.08320 (Scientific problem, assumptions and evaluation methodology: LHCO control-region collider anomalies)
- archive: https://zenodo.org/records/2629073 (events_anomalydetection.h5; source Pythia/Delphes constituents and R&D truth.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Bounded first50,000 author-shuffled R&D source events. Training retains actual source signal contamination; no detector-observation discovery or cross-generator generalization claim.
- Retrieved byte ranges and normalized pack are SHA256-verified. Full-source advertised MD5 is preserved but not claimed verified after partial download.
