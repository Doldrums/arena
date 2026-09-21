# Earth and environment: WeatherBench probabilistic forecast calibration

**Source collection:** [Earth observation and geophysical inference: source-based research tasks](../../papers/science-earth_data.md)\
**Task id:** `science-earth-weatherbench-calibration`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Calibrate fixed operational ensemble forecasts using prior-year history and evaluate their predictive distributions against independently aligned future-year reanalysis.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

calibrate(forecast,lead_hours,locations,training_history) -> finite n x1..128 ensemble. Fixed WeatherBench forecasts and ERA5 target, lat/lon locations and prior-year labeled training history. Exact empirical-ensemble CRPS, latitude weights, training-only extreme threshold and Brier diagnostic. No evaluation labels provided.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `public_benchmark`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Produce reliable probabilistic weather forecasts by correcting ensemble bias and spread.

Why it matters: Calibrated forecast uncertainty helps users reason about weather-dependent outcomes.

- [Calibrated Probabilistic Forecasting Using Ensemble Model Output Statistics and Minimum CRPS Estimation](https://journals.ametsoc.org/view/journals/mwre/133/5/mwr2904.1.xml): Main research objective: Correct bias and underdispersion in weather ensembles to improve predictive distributions. Task connection: The local IFS 2 m temperature task applies this forecast-calibration problem to a historical prior-year/future-year split with ERA5 verification. The paper does not validate the local alignment, reanalysis truth assumption or operational skill.

The cited primary paper develops or applies a solution to the stated scientific problem; its task is not merely an agent or general-purpose framework evaluation. Support concerns the scientific problem family, not a claim of new discovery or full-paper reproduction by this local task.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independent source-data adaptation. Source/metric/holdout details and actual run status in docs/EARTH_DATA.md. No synthetic substitution for promised measured datasets; missing data yields explicit setup failure.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:../../.cache/science-earth-data/E03.json`
- `file:../../.cache/science-earth-data/E03.manifest.json`

## Sources

- paper: https://arxiv.org/abs/2308.15560 (WeatherBench2 forecast evaluation, probabilistic ensembleCRPS, ERA5 reference data and area weighting.)
- benchmark: https://weatherbench2.readthedocs.io/en/latest/data-guide.html (Official source data/evaluation reference; evaluator and seed independently written.)
- paper: https://journals.ametsoc.org/view/journals/mwre/133/5/mwr2904.1.xml (Develops ensemble forecast postprocessing that corrects bias and dispersion using historical observations and CRPS. The local WeatherBench2 IFS/ERA5 chronological subset is a separate application of this calibration task.)

## Limitations

- IFS50-member2m-temperature24-hour forecasts on64×32 grid: monthly2018 training versus monthly2019 evaluation at64 locations. ERA5 is reanalysis, not independent raw weather observation. TIGGE data have research-use restrictions; this is a small chronological adaptation.
- Source data remain local caches with immutable revisions/content hashes and no evaluator network access. Public subsets are development-visible; freeze candidates before wider generalization tests.
- Improved source benchmark performance is a scientific-method contribution, not alone a new discovery or operational forecast validation.
