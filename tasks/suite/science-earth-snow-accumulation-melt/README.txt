# Earth science: Snow accumulation and melt across sites

**Source collection:** [Earth and environmental science: source-based research tasks](../../papers/science-earth_expansion.md)\
**Task id:** `science-earth-snow-accumulation-melt`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Snow accumulation and melt across sites with an explicit candidate interface, physical units, independent evaluator and source-traceable observations or numerical model.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

snow_step(meteorology, snow_state, site_parameters) -> {swe,melt,sublimation}, all mm water equivalent per step. Hourly snowfall and temperature; melt drains immediately. Enforce exact solid-water balance and nonnegative stores/fluxes. Site-winter macro RMSE against measured ESM-SnowMIP SWE; first31days spin up. Degree-day seed, four whole winters at two sites. This adaptation does not check energy conservation or reproduce every FSM2 process.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Predict snow-water storage and melt timing from meteorological forcing.

Why it matters: Snow accumulation and melt affect seasonal water supply and land-surface energy exchange.


The current citation introduces the ESM-SnowMIP intercomparison. The local four-site-winter protocol uses a simplified storage/melt budget without the energy and canopy processes of source snow models. Inspected problem-focused snow-albedo/topography papers address physical processes not represented or directly isolated here, so they were not substituted as generic snow-domain proof. No qualifying primary-goal evidence is established for this local task in this review; this is not a finding that the broader subject is unimportant.

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
- `file:../../.cache/science-earth/E09.json`
- `file:../../.cache/science-earth/E09.manifest.json`

## Sources

- paper: https://gmd.copernicus.org/articles/11/5027/2018/ (Scientific process, benchmark motivation and evaluation assumptions.)
- benchmark: https://doi.pangaea.de/10.1594/PANGAEA.897575 (Original source data/model; local candidate and evaluator are independently implemented.)

## Limitations

- Bounded adaptation; no complete source-paper score reproduction or novel scientific discovery claimed.
- Public evaluation cases are development instances; independent generalization requires frozen candidates and new cases.
- Four complete site-winters from ESM-SnowMIP; CC-BY-NC4.0 source observations.
