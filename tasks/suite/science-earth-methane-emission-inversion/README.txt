# Earth science: Methane emission inversion

**Source collection:** [Earth and environmental science: source-based research tasks](../../papers/science-earth_expansion.md)\
**Task id:** `science-earth-methane-emission-inversion`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Methane emission inversion with an explicit candidate interface, physical units, independent evaluator and source-traceable observations or numerical model.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

infer_emissions(columns, transport_operator, prior, uncertainty) -> 2..1024nonnegative emission samples. Frozen IMI/GEOS-Chem linear sensitivities include averaging kernels and quality filtering. Complete orbit groups withheld. Minimize independent held-out-column Gaussian-mixture negative log predictive density; predictive coverage/width diagnostics. No exact real-emission truth or nonlinear transport-reproduction claim.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer regional methane emissions from atmospheric satellite observations and transport modeling.

Why it matters: Quantifying emissions identifies discrepancies in inventories and supports understanding and mitigation of methane's climate effects.

- [Quantifying methane emissions from the largest oil-producing basin in the United States from space](https://pmc.ncbi.nlm.nih.gov/articles/PMC7176423/): Main research objective: Estimate methane emissions from oil and gas production in the Permian Basin using TROPOMI observations and atmospheric inverse modeling. Task connection: The local task defines the same observation-to-emission inversion family through a curated IMI case and transport operator. The required case remains unstaged; scientific relevance does not establish implementation readiness, reproducing the Permian estimate or correctness of an unprepared adapter.

The primary study estimates real emissions. The IMI software/facility introduction is not used as the qualifying evidence.

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
- `file:../../.cache/science-earth/E12.json`
- `file:../../.cache/science-earth/E12.manifest.json`

## Sources

- paper: https://gmd.copernicus.org/articles/15/5787/2022/ (Scientific process, benchmark motivation and evaluation assumptions.)
- repository: https://github.com/geoschem/integrated_methane_inversion (Original source data/model; local candidate and evaluator are independently implemented.)

## Limitations

- Bounded adaptation; no complete source-paper score reproduction or novel scientific discovery claimed.
- Public evaluation cases are development instances; independent generalization requires frozen candidates and new cases.
- Requires a curated source IMI case with quality masks, averaging kernels, precomputed GEOS-Chem operator and orbit split.
