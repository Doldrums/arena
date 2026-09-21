# Cosmology: universal luminosity-distance quadrature

**Source collection:** [Cosmology and astrophysics: source-based research tasks](../../papers/science-cosmology.md)\
**Task id:** `science-cosmology-luminosity-distance-quadrature`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Discover an eight-node positive quadrature rule for dimensionless luminosity distance in spatially flat, time-varying dark-energy models. The same nodes and weights must work across all models. Minimize the worst relative error against independent adaptive integration on disjoint public validation cosmologies. This is a locally designed synthetic numerical-method task reconstructed from published distance and CPL equations.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'nodes': length-8 real vector, 'weights': length-8 real vector}. Nodes must be strictly increasing in [0,1], weights positive and sum to 1 within 1e-12. One universal rule is used for every cosmology: dL/(c/H0) = (1+z)*z*sum_i weights[i]/E(a_i), where a_i=1/(1+z*nodes[i]) and E(a)=H(a)/H0. The evaluator computes integrands itself. Minimize worst relative validation error in percent; exactly eight integrand samples per distance.

Parameters: `{"n_nodes": 8}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `natural_science`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `cosmology_and_astrophysics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Compute luminosity distances accurately and efficiently in cosmologies with time-dependent dark energy.

Why it matters: Numerical luminosity-distance integration for CPL dark energy is the cited paper's central computational cosmology problem.

- [Quadrature algorithms to the luminosity distance with a time-dependent dark energy model](https://arxiv.org/abs/1109.6388): Main research objective: Develop and compare efficient, accurate numerical quadrature for luminosity distances with evolving dark energy. Task connection: The local task searches for one positive eight-node rule across a specified CPL model range. This universal fixed-node constraint and aggregate error objective are local restrictions, rather than the algorithms or accuracy claims of the paper.

The source addresses the same numerical observable directly, rather than mentioning cosmology as a generic optimizer test.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Local reduced benchmark reconstructed from Hogg distance equations and Linder's CPL expansion history, not the papers' experiments. Flat matter plus smooth dark energy, no radiation or neutrinos: a=1/(1+z), E(a)^2=Om*a^-3+(1-Om)*a^[-3(1+w0+wa)]*exp[-3*wa*(1-a)]. All distances are in c/H0 units; z, Om, w0, wa are dimensionless. Eight calibration and eight disjoint validation cosmologies (Om 0.18..0.42, w0 -1.30..-0.75, wa -0.30..0.30) and seven redshifts per split span z=0.01..10; full public tuples are in science_cosmology.py. Score=100*max(abs(prediction/reference-1)) on validation; calibration error is diagnostic. Reference: adaptive QUADPACK with 2e-12 absolute/relative tolerance. Node/weight optimization has a fixed inference budget, not a wall-clock performance claim. Validation is public, not a hidden generalization test; no real observations or open cosmological question are solved.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/abs/astro-ph/9905116 (Hogg, Distance measures in cosmology, v4; sections 4, 5 and 7, equations 15, 16 and 21: comoving and luminosity distance.)
- paper: https://arxiv.org/abs/astro-ph/0208512 (Linder, Exploring the Expansion History of the Universe; section B, equations 6 and 7 and following density evolution: w(a)=w0+wa(1-a).)
- paper: https://arxiv.org/abs/1109.6388 (Develops and compares Romberg and Gaussian quadrature for luminosity distance in CPL dark-energy models. The fixed universal eight-node rule and public cosmology split are local restrictions on that same numerical-method problem.)

## Limitations

- Local reduced benchmark, not original paper code, measurements, or a reproduction of a published benchmark score.
- Assumes a flat matter plus smooth CPL dark-energy background; omits radiation, spatial curvature and neutrino effects.
- The calibration and validation cosmologies are disjoint but public; repeated optimization against validation can overfit this finite suite.
- The metric tests numerical accuracy at fixed eight-sample inference cost, not measured speed or a resolution of the dark-energy problem.
