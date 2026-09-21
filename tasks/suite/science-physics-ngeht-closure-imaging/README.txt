# ngEHT closure-constrained imaging

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-ngeht-closure-imaging`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

reconstruct(visibilities, array_metadata, noise) -> nonnegative square image in Jy per pixel with calibrated total flux. Source data supply uv wavelengths, amplitudes, signed closure triangles and phases. Independent direct Fourier transform checks amplitude/closure likelihood and fixed-centre, resolution-matched image NRMSE. Source models/schedules split. Official ngEHT permission required before staging restricted challenge files.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

reconstruct(visibilities, array_metadata, noise) -> nonnegative square image in Jy per pixel with calibrated total flux. Source data supply uv wavelengths, amplitudes, signed closure triangles and phases. Independent direct Fourier transform checks amplitude/closure likelihood and fixed-centre, resolution-matched image NRMSE. Source models/schedules split. Official ngEHT permission required before staging restricted challenge files.

Parameters: `{"proposal_id": "P09"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `cosmology_and_astrophysics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Recover astronomical brightness structure from sparse interferometric observations with calibration-robust constraints.

Why it matters: Reconstructing images despite station calibration uncertainty is the direct astronomical inverse problem studied in the paper.

- [Interferometric Imaging Directly with Closure Phases and Closure Amplitudes](https://arxiv.org/abs/1803.07088): Main research objective: Develop interferometric image reconstruction using closure quantities that are insensitive to station-based calibration errors. Task connection: The local ngEHT task reconstructs a nonnegative, flux-constrained image from amplitudes and closure phases. Its fixed resolution, source data, and image score form a restricted adaptation; it does not use all closure-amplitude methods or reproduce an observed black-hole image.

The source solves an observational imaging problem; importance is not inferred from an ngEHT dataset description.

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
- `file:data/physics-expansion/P09/manifest.json`
- `file:data/physics-expansion/P09/benchmark.npz`

## Sources

- paper: https://arxiv.org/abs/2212.11355 (Scientific problem, assumptions and evaluation methodology: ngEHT closure-constrained imaging)
- archive: https://challenge.ngeht.org/challenge1/ (Challenge 1 data/model download permission is limited to invited participants; no unrestricted mirror assumed.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Source restricted to challenge participants; obtain explicit source permission/credentials, then curate fixed-FOV visibilities/closure/model data.
