# Earth and environment: Independent-track ocean surface-height reconstruction

**Source collection:** [Earth observation and geophysical inference: source-based research tasks](../../papers/science-earth_data.md)\
**Task id:** `science-earth-oceanbench-satellite-ssh`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Reconstruct measured sea-surface-height anomalies from irregular satellite observations and evaluate a fully withheld satellite system.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

reconstruct_ssh(observations,times,coordinates,grid) -> finite values at grid[coordinates,times]. Coordinates[latitude_deg,longitude_deg]; times are days since declared epoch; observed/returned sea-surface-height anomalies in meters. Withheld complete satellite system supplies evaluation tracks. PrimaryRMSE; independent-track OSE is incomplete truth, no full-field spectral-resolution claim.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Reconstruct ocean sea-level anomalies from irregular satellite altimetry tracks.

Why it matters: Sea-surface-height fields reveal ocean variability and support inference of ocean circulation.

- [An Improved Mapping Method of Multisatellite Altimeter Data](https://journals.ametsoc.org/abstract/journals/atot/15/2/1520-0426_1998_015_0522_aimmom_2_0_co_2.xml): Main research objective: Recover ocean sea-level signals from multisatellite altimetry while correcting along-track correlated measurement errors that obscure ocean features. Task connection: The paper directly reconstructs sea-level anomaly maps from measured TOPEX/Poseidon and ERS-1 tracks. The local task uses a different source/time period with a wholly withheld satellite; it does not reproduce the paper's error model, region or global analysis.

A physical oceanographic reconstruction paper supplies the evidence, rather than the OceanBench benchmark or a general learning framework.

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
- `file:../../.cache/science-earth-data/E06.json`
- `file:../../.cache/science-earth-data/E06.manifest.json`

## Sources

- paper: https://arxiv.org/abs/2309.15599 (OceanBench sea-surface-height reconstruction and distinct observing-system experiment versus simulation regimes.)
- repository: https://github.com/quentinf00/oceanbench-data-registry/tree/b678399e9264e8a1a04384cb4c1ca71a2773f302 (Official source data/evaluation reference; evaluator and seed independently written.)

## Limitations

- Real January2017GulfStream Jason2N observations to independently withheldJason3 tracks. Source filteredSLA in meters, retrospective reconstruction and source-order decimation. Independent tracks provide incomplete spatial truth; no full-fieldOSSE or spectral-resolution claim.
- Source data remain local caches with immutable revisions/content hashes and no evaluator network access. Public subsets are development-visible; freeze candidates before wider generalization tests.
- Improved source benchmark performance is a scientific-method contribution, not alone a new discovery or operational forecast validation.
