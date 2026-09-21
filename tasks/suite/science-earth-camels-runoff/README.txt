# Earth and environment: Measured rainfall–runoff transfer across catchments

**Source collection:** [Earth observation and geophysical inference: source-based research tasks](../../papers/science-earth_data.md)\
**Task id:** `science-earth-camels-runoff`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Calibrate a causal, water-conserving snow/soil runoff model on measured CAMELS catchments and predict discharge in wholly unseen basins and a subsequent year.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit_runoff(training_basins) -> callable runoff(forcing_history,basin_attributes,state). Daily forcing columns[precipitation_mm,mean_temperature_C,solar_Wm2]. Output dict discharge_mm>=0,evapotranspiration_mm>=0,state with total storage_mm>=0. Enforce storage_previous+P-Q-ET=storage_new to1e-5mm. Retrospective current-day forcing only; full unseen-basin/year holdout. Basin-macro NSE, extremes and water-balance diagnostics.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Predict catchment runoff across basins from meteorological forcing.

Why it matters: Hydrological prediction supports understanding of basin behavior and estimation of water availability.

- [Towards learning universal, regional, and local hydrological behaviors via machine learning applied to large-sample datasets](https://hess.copernicus.org/articles/23/5089/2019/): Main research objective: Predict runoff and investigate hydrological behaviors that transfer across catchments. Task connection: The paper directly models runoff across CAMELS basins. The local water-conserving model uses four observed basins and withheld basins/year; this restricted sample cannot reproduce the paper's broad regional-generalization results.

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
- `file:../../.cache/science-earth-data/E01.json`
- `file:../../.cache/science-earth-data/E01.manifest.json`

## Sources

- paper: https://hess.copernicus.org/articles/21/5293/2017/ (CAMELS-US dataset description, catchment attributes, meteorological forcing and streamflow observations.)
- repository: https://github.com/neuralhydrology/neuralhydrology/tree/37568bcb2a207a82b92cac3e4ef52fb8fc8662b5/test/test_data/camels_us (Official source data/evaluation reference; evaluator and seed independently written.)
- paper: https://hess.copernicus.org/articles/23/5089/2019/ (Develops rainfall-runoff models across CAMELS catchments and evaluates regional and ungauged-basin transfer. The local four-basin causal water-conserving model is a much smaller task-family adaptation.)

## Limitations

- Four source basins2000–2002; two training basins and two wholly unseen evaluation basins. Daily retrospective forcing, not meteorological forecasting. Tiny geographic sample is not the full671-basin benchmark.
- Source data remain local caches with immutable revisions/content hashes and no evaluator network access. Public subsets are development-visible; freeze candidates before wider generalization tests.
- Improved source benchmark performance is a scientific-method contribution, not alone a new discovery or operational forecast validation.
