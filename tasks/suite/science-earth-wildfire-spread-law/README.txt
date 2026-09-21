# Earth science: Measured wildfire spread laws

**Source collection:** [Earth and environmental science: source-based research tasks](../../papers/science-earth_expansion.md)\
**Task id:** `science-earth-wildfire-spread-law`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Measured wildfire spread laws with an explicit candidate interface, physical units, independent evaluator and source-traceable observations or numerical model.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit_spread(training_features, training_rates, metadata) -> object.spread_rate(features). Five measured inputs: wind m/s, measurement height m, dead-fuel moisture fraction, fuel height m, dry load kg/m2. Return nonnegative m/s. Equal-country RMSE on complete held-out countries from Anderson2015. Missing inputs excluded; no invented fuel or slope inputs.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Predict shrubland wildfire spread rates from measured environmental and fuel conditions.

Why it matters: Fire-spread prediction informs understanding of fire behavior and planning for fire hazards.

- [A generic, empirical-based model for predicting rate of fire spread in shrublands](https://doi.org/10.1071/WF14130): Main research objective: Develop and validate empirical shrubland fire-spread predictions using measured fires. Task connection: The local task fits spread laws to measured Anderson2015 shrubland observations. It is a bounded source adaptation, not an operational fire forecast or validation for fuels outside the observed conditions.

The cited primary paper develops or applies a solution to the stated scientific problem; its task is not merely an agent or general-purpose framework evaluation. Support concerns the scientific problem family, not a claim of new discovery or full-paper reproduction by this local task.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independent candidate/evaluator implementation with attributed source data or fixed scientific simulators. See docs/EARTH_EXPANSION.md for setup, units, splits, licenses and scientific limits. Public cases are development benchmarks; freezing candidates and new cases is required for generalization claims.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:../../.cache/science-earth/E07.json`
- `file:../../.cache/science-earth/E07.manifest.json`

## Sources

- paper: https://doi.org/10.1071/WF14130 (Scientific process, benchmark motivation and evaluation assumptions.)
- repository: https://github.com/wirc-sjsu/firebench (Original source data/model; local candidate and evaluator are independently implemented.)

## Limitations

- Bounded adaptation; no complete source-paper score reproduction or novel scientific discovery claimed.
- Public evaluation cases are development instances; independent generalization requires frozen candidates and new cases.
- CPU, measured Anderson2015 shrubland fires; commercial-use permissions apply.
