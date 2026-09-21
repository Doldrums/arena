# Critical-regime XY Monte Carlo schedules

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-xy-critical-monte-carlo`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

schedule(temperature, lattice_size, budget) -> list of 1..64 kernel names: metropolis, overrelax, wolff, containing a stochastic kernel. Trusted detailed-balance kernels operate classical periodic XY model. Each sweep/cluster is charged N site units (upper bound); warmup counts. Multiple independent chains score squared energy/magnetization errors against long independent reference chains, with reference uncertainty and autocorrelation diagnostics. Fixed-work local adaptation, not a timing leaderboard.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

schedule(temperature, lattice_size, budget) -> list of 1..64 kernel names: metropolis, overrelax, wolff, containing a stochastic kernel. Trusted detailed-balance kernels operate classical periodic XY model. Each sweep/cluster is charged N site units (upper bound); warmup counts. Multiple independent chains score squared energy/magnetization errors against long independent reference chains, with reference uncertainty and autocorrelation diagnostics. Fixed-work local adaptation, not a timing leaderboard.

Parameters: `{"proposal_id": "P14"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `physics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Sample critical spin-model equilibria efficiently despite long autocorrelation times.

Why it matters: Reducing critical slowing in physical spin-system sampling is the main goal of the Wolff algorithm paper.

- [Collective Monte Carlo Updating for Spin Systems](https://doi.org/10.1103/PhysRevLett.62.361): Main research objective: Improve equilibrium Monte Carlo sampling near criticality through collective spin-cluster updates, including the XY model. Task connection: The local task schedules trusted Metropolis, overrelaxation, and Wolff kernels for finite XY systems under a work budget. It optimizes a restricted mixture of existing kernels; its schedule search and equilibrium-error score are not the paper's new cluster algorithm.

The primary target is efficient physical equilibrium sampling. The local schedule is explicitly an adaptation of that research problem.

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
- `file:data/physics-expansion/P14/manifest.json`
- `file:data/physics-expansion/P14/benchmark.npz`

## Sources

- paper: https://doi.org/10.1103/PhysRevLett.62.361 (Scientific problem, assumptions and evaluation methodology: Critical-regime XY Monte Carlo schedules)
- repository: https://alps.comp-phys.org/tutorials/mcs/ (Classical XY Wolff kernel and equilibrium Monte Carlo methodology; independent fixed-work implementation.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Run scripts/prepare_physics_expansion.py --xy-reference to create long-chain numerical reference with uncertainty checks.
