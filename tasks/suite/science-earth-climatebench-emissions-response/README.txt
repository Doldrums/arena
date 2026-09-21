# Earth and environment: ClimateBench emissions-to-climate response

**Source collection:** [Earth observation and geophysical inference: source-based research tasks](../../papers/science-earth_data.md)\
**Task id:** `science-earth-climatebench-emissions-response`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Learn a compact emissions-response emulator from complete training scenarios and predict source climate anomalies for the entirely withheldSSP245 scenario.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit_climate(training_scenarios,grid) -> model.project_climate(forcing_history) returning declared year x latitude x longitude fields. Input named columns cumulativeCO2,CH4,globalSO2,globalBC. NorESM source climate anomalies, tas inK and precipitation inmm/day. Complete SSP245 withheld; score2080–2100 using cos(latitude)-weighted spatialNRMSE+5*globalNRMSE, then mean variables. Four-variable full leaderboard not claimed for two-variable coarse subset.

## Labels

Scientific contribution: `method` (tier 2); artifact `model`, domain `natural_science`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Predict spatial climate temperature responses to greenhouse-gas and aerosol emissions.

Why it matters: Resolving regional emissions responses helps understand how different emissions pathways affect future climate.

- [Emulation of the Climate Response to Greenhouse Gas and Aerosol Emissions From High- and Low-Income Nations](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2025GL117841): Main research objective: Separate and predict spatiotemporal temperature impacts of greenhouse gases and aerosols associated with different emitting regions. Task connection: The paper solves emissions-to-temperature emulation for CESM2 experiments. The local task instead uses ClimateBench scenarios and a withheld SSP245 response; it tests the same physical response family without reproducing the paper's regional attribution or climate model.

The qualifying paper pursues a climate-response and attribution question. The ClimateBench benchmark paper itself is excluded.

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
- `file:../../.cache/science-earth-data/E05.json`
- `file:../../.cache/science-earth-data/E05.manifest.json`

## Sources

- paper: https://doi.org/10.1029/2021MS002954 (ClimateBench1.0 problem definition, scenario-level split and spatial/global normalized error, Sections2–4.)
- repository: https://github.com/duncanwp/ClimateBench/blob/085c0b5b20761446fabe05bbc58b9a5440e9c25f/analysis_notebooks/paper_figures.ipynb (Official source data/evaluation reference; evaluator and seed independently written.)

## Limitations

- Source NorESM member means, temperature/precipitation anomalies, area-weighted8×12 spatial adaptation. CompleteSSP245 held out;2080–2100 scored. TrainingSSP370 uses available-member means because two source members end early. Not the full-resolution four-variable leaderboard or observed future climate.
- Source data remain local caches with immutable revisions/content hashes and no evaluator network access. Public subsets are development-visible; freeze candidates before wider generalization tests.
- Improved source benchmark performance is a scientific-method contribution, not alone a new discovery or operational forecast validation.
