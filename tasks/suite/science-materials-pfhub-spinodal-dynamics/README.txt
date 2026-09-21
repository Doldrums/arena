# PFHub spinodal decomposition integration

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-pfhub-spinodal-dynamics`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

evolve_composition(initial_field, parameters, times) -> array (len(times),N,N). Integrate dc/dt=M*L[f'(c)-kappa*L(c)] using the specified second-order periodic discrete Laplacian on [0,200)^2; f=rho*(c-alpha)^2*(c-beta)^2 with alpha=.3,beta=.7,rho=5,M=5,kappa=2. Score candidate wall time only when RMSE<=2e-5 versus independent DOP853, mass drift<1e-9 and discrete free energy never increases. Two fixed meshes 48 and 64, published initial condition and a phase-shift adaptation, times 1,5,20. These are explicit short-horizon, fixed-mesh adaptations, not a reproduction of PFHub equilibrium results.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

evolve_composition(initial_field, parameters, times) -> array (len(times),N,N). Integrate dc/dt=M*L[f'(c)-kappa*L(c)] using the specified second-order periodic discrete Laplacian on [0,200)^2; f=rho*(c-alpha)^2*(c-beta)^2 with alpha=.3,beta=.7,rho=5,M=5,kappa=2. Score candidate wall time only when RMSE<=2e-5 versus independent DOP853, mass drift<1e-9 and discrete free energy never increases. Two fixed meshes 48 and 64, published initial condition and a phase-shift adaptation, times 1,5,20. These are explicit short-horizon, fixed-mesh adaptations, not a reproduction of PFHub equilibrium results.

Parameters: `{"proposal_id": "C06"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `materials_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Solve Cahn-Hilliard phase-separation dynamics while retaining conservation and energy dissipation.

Why it matters: Phase-field dynamics describe the development of material microstructures during separation of mixtures.

- [Applications of semi-implicit Fourier-spectral method to phase field equations](https://doi.org/10.1016/S0010-4655(97)00115-X): Main research objective: Accurately and efficiently simulate physical phase-field evolution, including Cahn-Hilliard spinodal decomposition. Task connection: The local task evolves the same physical equation class on fixed two-dimensional periodic finite-difference meshes. Its short times and discrete operator differ from the paper's Fourier method; runtime gains are meaningful only after local trajectory, mass and energy checks.

The cited method is designed to solve phase-evolution equations, not to assess a general agent. PFHub benchmark metadata alone is not used as evidence.

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
- `py:scipy`

## Sources

- paper: https://arxiv.org/abs/1610.00622 (Benchmark problems for numerical implementations of phase field models, spinodal decomposition.)
- benchmark: https://pages.nist.gov/pfhub/benchmarks/benchmark1.ipynb/ (Benchmark 1, free energy and dynamics, parameter table, initial condition and square-periodic case 1a. Our mesh/time/phase-shift choices are local adaptations.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Fixed-mesh 48/64-point periodic short-horizon adaptation (times 1,5,20), with a second phase-shifted initial field. Does not reproduce PFHub equilibrium or nonperiodic/geometric cases.
- The reference resolves time integration of the specified spatial discretization; it is not claimed to be a continuum grid-converged reference.
