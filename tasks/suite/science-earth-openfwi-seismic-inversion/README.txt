# Earth and environment: OpenFWI subsurface seismic inversion

**Source collection:** [Earth observation and geophysical inference: source-based research tasks](../../papers/science-earth_data.md)\
**Task id:** `science-earth-openfwi-seismic-inversion`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Reconstruct a positive subsurface velocity field from simulated seismic traces, independently checking velocity structure and a pinned source-matching wave forward model.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

invert_seismograms(traces,source_receiver_geometry,forward_oracle,budget) -> positive velocity grid in m/s. geometry includes grid_shape and velocity_bounds. Independent source-matching trusted forward solver is checksum-pinned. Enforce oracle-call limit, velocity bounds; primary velocity NRMSE, gradient and forward-waveform diagnostics. Requires actual OpenFWI arrays/geometry/simulator; no toy PDE fallback.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer subsurface seismic velocity structure from recorded waveforms.

Why it matters: Seismic velocity reconstruction helps investigate the structure and properties of the subsurface.

- [InversionNet: A Real-Time and Accurate Full Waveform Inversion with CNNs and Continuous CRFs](https://arxiv.org/abs/1811.07875): Main research objective: Reconstruct subsurface velocity models from seismic waveforms while addressing computational and resolution limitations of inversion. Task connection: The local task retains the physical waveform-to-velocity inverse problem with a forward-wave consistency check on simulated source traces. It does not establish performance on measured field seismic data or reproduce the paper's full study.

A domain-specific seismic inverse solver is the evidence; the OpenFWI benchmark introduction alone is excluded.

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
- `file:../../.cache/science-earth-data/E04.json`
- `file:../../.cache/science-earth-data/E04.manifest.json`

## Sources

- paper: https://arxiv.org/abs/2111.02926 (OpenFWI dataset geometry, synthetic geological models, wave simulation and inversion metrics.)
- benchmark: https://openfwi-lanl.github.io/docs/data.html (Official source data/evaluation reference; evaluator and seed independently written.)

## Limitations

- Needs actual OpenFWI arrays and a validated source-matching forward simulator; smallest advertisedVel dataset43GB. No locally generated toy wavefields substituted. Source data areCC-BY-NC-SA4.0; no field-survey truth claim.
- Source data remain local caches with immutable revisions/content hashes and no evaluator network access. Public subsets are development-visible; freeze candidates before wider generalization tests.
- Improved source benchmark performance is a scientific-method contribution, not alone a new discovery or operational forecast validation.
