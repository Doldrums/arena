# Expansion-history models fitted to the Pantheon+ supernova Hubble diagram

**Source collection:** [Cosmology and astrophysics: source-based research tasks](../../papers/science-cosmology.md)\
**Task id:** `science-cosmology-pantheon-plus-expansion-fit`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Propose a parametric expansion history E(z) = H(z)/H0 with at most six parameters and fit it to the 1,580 Pantheon+ Type Ia supernova light curves with zHD > 0.01 (the 1,590-object cosmology sample minus the ten Cepheid-host calibrators) (corrected apparent magnitudes and the full statistical plus systematic covariance). The absolute magnitude is profiled analytically; the score is the minimum chi-squared, lower is better. Flat LambdaCDM with a fitted matter density is reported for comparison.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

expansion(z, theta) -> array E(z) = H(z)/H0 for an array of redshifts z >= 0 (positive, finite; E(0) should be 1); initial_theta() -> initial parameter vector (1 to 6 values); bounds() -> list of (low, high) per parameter. The evaluator fits theta to the Pantheon+ Hubble diagram (zHD > 0.01 and no Cepheid calibrators: 1,580 light curves, STAT+SYS covariance) with the absolute magnitude profiled analytically and H0 = 70 fixed for the distance scale; score is the minimum chi-squared (lower is better). Flat LambdaCDM (fitted Omega_m) chi-squared is reported for comparison.

Parameters: `{"z_min": 0.01}`

## Labels

Scientific contribution: `discovery` (tier 1); artifact `equation`, domain `natural_science`, data `real_measurements`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `cosmology_and_astrophysics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Constrain cosmic expansion and dark energy using Type Ia supernova distance measurements.

Why it matters: Inferring cosmological parameters from supernova observations is the primary goal of the Pantheon+ cosmology analysis.

- [The Pantheon+ Analysis: Cosmological Constraints](https://arxiv.org/abs/2202.04077): Main research objective: Use the Pantheon+ supernova sample to infer cosmological parameters, including dark-energy properties. Task connection: The local task fits a bounded-complexity expansion history to a selected set of Pantheon+ light curves with covariance and a profiled magnitude offset. Its Cepheid-host exclusion, parameter cap, and chi-square objective do not reproduce the full combined cosmological analysis.

The chosen source is the cosmological-inference paper, not merely the Pantheon+ data-release paper.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Real Pantheon+ measurements (Brout et al. 2022) fetched by scripts/prepare_science_data.py from the public release at a pinned commit. The likelihood follows the release's recommended use (corrected magnitudes m_b_corr, full covariance, zHD > 0.01), with the absolute magnitude profiled and H0 fixed; it is not the published Pantheon+ cosmology pipeline and the SH0ES calibrator likelihood is omitted.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:data/pantheon-plus/Pantheon+SH0ES.dat`
- `file:data/pantheon-plus/Pantheon+SH0ES_STAT+SYS.npy`

## Sources

- paper: https://arxiv.org/abs/2202.04077 (Brout et al. 2022, The Pantheon+ Analysis: Cosmological Constraints; Section 2 (data), Section 3 (likelihood with the STAT+SYS covariance, zHD > 0.01 cut).)
- repository: https://github.com/PantheonPlusSH0ES/DataRelease/tree/c447f0fea703fcd0fff57de5000947b5ca81286b/Pantheon%2B_Data/4_DISTANCES_AND_COVAR (Pantheon+SH0ES.dat and Pantheon+SH0ES_STAT+SYS.cov, fetched by scripts/prepare_science_data.py and pinned by SHA-256.)

## Limitations

- Real measurements: the data are the public Pantheon+ release, fetched at prepare time (network), not redistributed.
- The likelihood profiles the absolute magnitude and fixes H0 = 70 for the distance scale, so only the shape of E(z) is constrained; the SH0ES Cepheid calibrators are excluded.
- A lower chi-squared than LambdaCDM with more parameters is not by itself evidence for new physics; model comparison needs an information criterion or Bayesian evidence, which the evaluator reports the ingredients for (chi-squared and parameter count).
