# GREAT3 weak-lensing shear calibration

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-great3-shear-calibration`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

estimate_shear(images, psf, metadata) -> [g1,g2] per GREAT3 subfield. Images have (galaxy,y,x) axes; PSF is a source stamp. Noise-cancellation groups remain intact. Independent evaluator rotates shear into PSF frame and computes official ground constant-shear Qc with multiplicative/additive bias diagnostics. No variable-shear claim.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

estimate_shear(images, psf, metadata) -> [g1,g2] per GREAT3 subfield. Images have (galaxy,y,x) axes; PSF is a source stamp. Noise-cancellation groups remain intact. Independent evaluator rotates shear into PSF frame and computes official ground constant-shear Qc with multiplicative/additive bias diagnostics. No variable-shear claim.

Parameters: `{"proposal_id": "P01"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `cosmology_and_astrophysics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer weak gravitational lensing shear from noisy, PSF-convolved galaxy images while controlling calibration bias.

Why it matters: Shear measurement and its calibration are the central research problem in metacalibration, rather than incidental tests of a general model.

- [Practical Weak Lensing Shear Measurement with Metacalibration](https://arxiv.org/abs/1702.02601): Main research objective: Develop and validate shear measurements that correct measurement response, selection effects, and correlated noise. Task connection: The local GREAT3 constant-ground image and PSF task addresses this shear-calibration problem. Its particular branch, Qc score, and compute restrictions are local evaluation choices; it does not reproduce the paper's complete analysis.

The paper proposes a solution to biased astronomical shear estimation. The GREAT3 dataset paper alone is not the importance evidence.

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
- `file:data/physics-expansion/P01/manifest.json`
- `file:data/physics-expansion/P01/benchmark.npz`

## Sources

- paper: https://academic.oup.com/mnras/article/450/3/2963/1064967 (Scientific problem, assumptions and evaluation methodology: GREAT3 weak-lensing shear calibration)
- archive: https://github.com/barnabytprowe/great3-public (Constant ground branch metric and noise-cancellation groups; Qc normalization 1.232.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Prepare complete GREAT3 subfields, source shears/PSF angles and disjoint noise-cancellation group labels; official legacy data host timed out during audit.
