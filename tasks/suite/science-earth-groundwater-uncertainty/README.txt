# Earth science: Groundwater predictive uncertainty

**Source collection:** [Earth and environmental science: source-based research tasks](../../papers/science-earth_expansion.md)\
**Task id:** `science-earth-groundwater-uncertainty`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Groundwater predictive uncertainty with an explicit candidate interface, physical units, independent evaluator and source-traceable observations or numerical model.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

infer_aquifer(head_observations, geometry, forward_oracle, budget) -> 2..8samples of four positive multipliers[.5,2]: three conductivity layers and recharge. Actual MF6 6.7.0 source Freyberg model. Eight search forward calls per case; verification calls separately charged/reported. Minimize held-out-head Gaussian-mixture negative log predictive density, noise0.1m;90%interval coverage/width and mass balance diagnostics. Two explicitly synthetic aquifers, final stress-period observations withheld.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Infer groundwater-model parameters and quantify uncertainty in predicted aquifer behavior.

Why it matters: Groundwater prediction can inform water-resource decisions when subsurface properties are uncertain.


The local Freyberg aquifers are synthetic workflow examples. Its original source is a PEST++ tutorial, and the additional ensemble-smoother paper primarily introduces a model-independent inference method. No inspected paper establishes the local synthetic instance as an attempt to answer a substantive aquifer or resource-management question. No qualifying primary-goal evidence is established for this local task in this review; this is not a finding that the broader subject is unimportant.

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
- `py:flopy`
- `file:../../.cache/science-earth/E11.json`
- `file:../../.cache/science-earth/E11.manifest.json`

## Sources

- paper: https://www.usgs.gov/publications/jupyter-notebooks-parameter-estimation-uncertainty-analysis-and-optimization-pest (Scientific process, benchmark motivation and evaluation assumptions.)
- repository: https://github.com/pypest/pyemu_pestpp_workflow (Original source data/model; local candidate and evaluator are independently implemented.)
- paper: https://www.sciencedirect.com/science/article/pii/S1364815218302676 (Develops and tests groundwater-model parameter inference and predictive uncertainty estimation, including synthetic groundwater examples. The local problem is a restricted inference protocol.)

## Limitations

- Bounded adaptation; no complete source-paper score reproduction or novel scientific discovery claimed.
- Public evaluation cases are development instances; independent generalization requires frozen candidates and new cases.
- Pinned MODFLOW6.7.0 binary and Freyberg model inputs; synthetic aquifers.
