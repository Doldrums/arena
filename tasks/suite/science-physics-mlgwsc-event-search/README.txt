# MLGWSC gravitational-wave event search

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-mlgwsc-event-search`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

search(h1, l1, metadata) -> N x 2 GPS time/ranking statistic array. Independent source observing blocks and source injections; triggers clustered and uniquely associated. Score sensitive distance at fixed FAR. At least 10 expected false alarms at the declared FAR must fit in the background duration; tiny noise clips cannot establish rare-event performance.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

search(h1, l1, metadata) -> N x 2 GPS time/ranking statistic array. Independent source observing blocks and source injections; triggers clustered and uniquely associated. Score sensitive distance at fixed FAR. At least 10 expected false alarms at the declared FAR must fit in the background duration; tiny noise clips cannot establish rare-event performance.

Parameters: `{"proposal_id": "P02"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `cosmology_and_astrophysics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Detect gravitational waves from merging binary black holes in noisy interferometer observations.

Why it matters: Recovering astrophysical merger signals from detector noise is the paper's central physical detection problem.

- [Detecting and denoising gravitational wave signals from binary black holes using deep learning](https://journals.aps.org/prd/abstract/10.1103/PhysRevD.108.043024): Main research objective: Develop a detection and denoising method for binary-black-hole gravitational waves and test recovery of observed signals. Task connection: The local event search uses MLGWSC source blocks and a sensitive-distance objective at fixed false-alarm rate. It pursues the same detection problem but uses a different data selection, search interface, and scoring protocol from this paper.

The evidence is a domain-specific attempt to recover physical signals, not merely the announcement of a challenge dataset.

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
- `file:data/physics-expansion/P02/manifest.json`
- `file:data/physics-expansion/P02/benchmark.npz`

## Sources

- paper: https://arxiv.org/abs/2209.11146 (Scientific problem, assumptions and evaluation methodology: MLGWSC gravitational-wave event search)
- archive: https://github.com/gwastro/ml-mock-data-challenge-1 (MLGWSC-1 Dataset 4 source real-noise foreground/background; evaluation sensitive distance.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Prepare source MLGWSC foreground/background with actual injection volume weights and long background; short clips cannot resolve declared FAR.
