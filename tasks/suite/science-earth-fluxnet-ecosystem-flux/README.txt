# Earth and environment: Measured ecosystem carbon-flux reconstruction

**Source collection:** [Earth observation and geophysical inference: source-based research tasks](../../papers/science-earth_data.md)\
**Task id:** `science-earth-fluxnet-ecosystem-flux`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Predict half-hourly net ecosystem carbon exchange from meteorology and ecosystem metadata, scoring quality-controlled measured targets rather than gap-filled products.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit_flux(training_sites) -> model.predict_flux(meteorology,ecosystem_metadata,history). Half-hourly FLUXNET columns[air_temperature_C,shortwave_Wm2,...]; net ecosystem CO2 exchange target in source units, can be negative. Only targetQC0 measured points score; no gap-filled values. Minimize site-macro RMSE divided by training-target standard deviation; complete sites/year blocks held out.

## Labels

Scientific contribution: `method` (tier 2); artifact `equation`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate net ecosystem carbon-dioxide exchange from meteorology and ecosystem conditions.

Why it matters: Ecosystem carbon exchange is needed to understand terrestrial contributions to the carbon cycle.

- [Modeling net ecosystem exchange of CO2 with gated recurrent unit neural networks](https://www.sciencedirect.com/science/article/pii/S016819232400100X): Main research objective: Predict measured net ecosystem CO2 exchange in bioenergy-crop systems. Task connection: The paper directly predicts half-hourly ecosystem exchange. The local task generalizes that target to a separately prepared FLUXNET site subset; it does not reproduce the study's Michigan crop sites or establish a global carbon budget.

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
- `file:../../.cache/science-earth-data/E02.json`
- `file:../../.cache/science-earth-data/E02.manifest.json`

## Sources

- paper: https://doi.org/10.1038/s41597-020-0534-3 (FLUXNET2015/ONEFlux data processing, flux-variable definitions, quality flags and measurement uncertainty.)
- benchmark: https://fluxnet.org/data/fluxnet2015-dataset/ (Official source data/evaluation reference; evaluator and seed independently written.)
- paper: https://www.sciencedirect.com/science/article/pii/S016819232400100X (Trains and evaluates half-hourly net ecosystem carbon-exchange prediction from environmental inputs. This establishes the prediction task family; the local FLUXNET sites, measured-target quality filters and site/year holdouts are separate protocol choices.)

## Limitations

- Requires source half-hourly tower files and site/year splits; only QC0 measured targets score. Net carbon exchange is distinct from derivedGPP/respiration. Official download endpoint returnedHTTP403 during staging.
- Source data remain local caches with immutable revisions/content hashes and no evaluator network access. Public subsets are development-visible; freeze candidates before wider generalization tests.
- Improved source benchmark performance is a scientific-method contribution, not alone a new discovery or operational forecast validation.
