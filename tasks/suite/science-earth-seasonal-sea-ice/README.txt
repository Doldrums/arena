# Earth science: Seasonal Arctic sea-ice probabilities

**Source collection:** [Earth and environmental science: source-based research tasks](../../papers/science-earth_expansion.md)\
**Task id:** `science-earth-seasonal-sea-ice`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Seasonal Arctic sea-ice probabilities with an explicit candidate interface, physical units, independent evaluator and source-traceable observations or numerical model.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

forecast_ice(history, past_climate_covariates, lead_months) -> (448,304) probabilities in[0,1] for monthly concentration>=0.15. Six actual NOAA/NSIDC G02202 v02r00 forecasts: July-December2013/2014 monthly histories predict next-year January/March/June at1/3/6-month leads. Native25km grid; area-weighted Brier over valid ocean north of60N using ellipsoidal cell areas, projected-km symmetric edge-distance diagnostic. Land/coast/pole-hole/missing flags excluded. Zeros outside supplied history_ocean_mask are placeholders. No future fields cross API. Historical NOAA observational adaptation, not original IceNet OSISAF data or leaderboard reproduction.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Forecast seasonal Arctic sea-ice occurrence probabilities.

Why it matters: Sea-ice forecasts support understanding and planning around changing Arctic marine conditions.

- [Seasonal Arctic sea ice forecasting with probabilistic deep learning](https://www.nature.com/articles/s41467-021-25257-4): Main research objective: Predict Arctic sea-ice conditions months ahead with calibrated spatial probabilities. Task connection: The local task forecasts satellite-observed ice on six historical cases at one-, three- and six-month leads. It uses NOAA/NSIDC Version 2 CDR rather than the paper's original source and does not establish operational skill or generalization across unseen years.

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
- `file:../../.cache/science-earth/E08.json`
- `file:../../.cache/science-earth/E08.manifest.json`

## Sources

- paper: https://www.nature.com/articles/s41467-021-25257-4 (Scientific process, benchmark motivation and evaluation assumptions.)
- repository: https://github.com/tom-andersson/icenet-paper (Original source data/model; local candidate and evaluator are independently implemented.)
- corpus: https://nsidc.org/data/g02202/versions/2 (Meier et al.2013, G02202 Version2 DOI10.7265/N55M63M1. Source monthly unedited CDR concentration, flags, projection and license; exact18files pinned locally.)
- paper: https://essd.copernicus.org/articles/5/311/2013/ (Peng et al.2013 NOAA/NSIDC CDR algorithms, monthly concentrations, quality limitations and reproducibility.)
- archive: https://www.ncei.noaa.gov/data/sea-ice-concentration/access/ (Official NOAA NCEI v02r00 monthly files: July-December2013/2014 and January/March/June2014/2015. SHA256 pins in data/science/earth_expansion/seaice_sources.json.)

## Limitations

- Historical NOAA/NSIDC G02202 v02r00 observational adaptation, not the original IceNet OSISAF dataset or full-paper score reproduction.
- Six fixed public chronological development cases at1/3/6-month leads; independent generalization requires frozen candidates and unseen years.
- Version2 is superseded and is not current operational data. Satellite retrieval and summer melt uncertainty remain; pole-hole, land/coastal and missing cells are excluded.
- Only valid Arctic ocean north of60N is scored; historical invalid cells have explicit masked zero placeholders. Edge diagnostic uses projected, not great-circle, distances.
