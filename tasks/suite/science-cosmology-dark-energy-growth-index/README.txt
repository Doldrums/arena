# Cosmology: compact dark-energy growth approximation

**Source collection:** [Cosmology and astrophysics: source-based research tasks](../../papers/science-cosmology.md)\
**Task id:** `science-cosmology-dark-energy-growth-index`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Improve a six-coefficient growth-index formula for the linear growth rate and normalized growth factor in smooth CPL dark-energy cosmologies. A tightly integrated general-relativistic second-order ODE provides an independent numerical reference. The score is the worst relative error across both observables on disjoint public validation cosmologies, extending the constant-gamma seed within a fixed compact ansatz.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> real vector of six finite coefficients in [-10,10]. At scale factor a, q=1-Om(a), u=1+w0+wa*(1-a), gamma=c0+c1*q+c2*q^2+c3*u+c4*wa*a+c5*u*q, and f=Om(a)^gamma. Gamma must lie in [0.1,1.2] at all checked locations. The evaluator computes D(a)/D(1)=exp(-integral_ln(a)^0 f(exp(x)) dx). Minimize 100 times the maximum relative error of both f and normalized D over validation models and a values.

## Labels

Scientific contribution: `method` (tier 2); artifact `equation`, domain `natural_science`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `cosmology_and_astrophysics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Approximate cosmological structure growth across dark-energy models with accurate compact formulas.

Why it matters: Describing linear growth and its relation to gravity and cosmic expansion is the paper's main scientific purpose.

- [Parameterized Beyond-Einstein Growth](https://arxiv.org/abs/astro-ph/0701317): Main research objective: Develop a compact growth-index description that separates cosmic expansion from the growth of density perturbations. Task connection: The local task fits six coefficients against growth ODEs for general-relativistic CPL cosmologies. It is a restricted approximation problem and does not reproduce the paper's wider modified-gravity analyses or establish evidence for new gravity.

The paper directly pursues the growth parameterization problem; the local ansatz is not itself a published scientific result.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Local six-coefficient approximation problem inspired by Linder and Cahn, not a reproduced paper benchmark. Spatially flat GR, pressureless matter and smooth CPL dark energy; no modified gravity, radiation, neutrinos or dark-energy clustering. E(a)^2=Om*a^-3+(1-Om)*a^[-3(1+w0+wa)]*exp[-3*wa*(1-a)], Om(a)=Om*a^-3/E(a)^2; all variables are dimensionless. The independent reference solves D_xx+(2+dlnH/dx)*D_x-(3/2)*Om(a)*D=0, x=ln(a), dlnH/dx=-(3/2)*(1+w(a)*(1-Om(a))), with D(0.001)=D_x(0.001)=0.001, then normalizes D(1)=1. DOP853 tolerances are rtol=2e-11, atol=1e-13. The candidate ansatz is integrated by 48-point Gauss-Legendre quadrature. Eight calibration models at 25 scale factors and eight disjoint public validation models at 33 scale factors span a=0.2..1. Calibration error is diagnostic; score is the worst validation error across growth and growth rate. Model tuples are in science_cosmology.py. This synthetic method task neither uses observational data nor resolves the nature of dark energy.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/abs/astro-ph/0701317 (Linder and Cahn, Parameterized Beyond-Einstein Growth; equations 1-3 and 8: growth-index ansatz and GR growth equation; equations 14-15: constant growth-index approximation.)
- paper: https://arxiv.org/abs/astro-ph/0208512 (Linder, Exploring the Expansion History of the Universe; equations 6 and 7 and following density evolution define the CPL background.)

## Limitations

- Local synthetic approximation task, not an observational discovery or reproduction of a paper's fitted coefficients.
- Uses general relativity, flat space and smooth dark energy; excludes nonlinear structure, modified gravity, radiation and neutrino effects.
- The numerical reference uses the explicitly specified finite matter-era boundary D(ai)=D_x(ai)=ai at ai=0.001; it is not a full Boltzmann cosmology solver.
- Calibration and validation models are disjoint but public. Better scores establish accuracy only on this finite model set and do not resolve the dark-energy problem.
