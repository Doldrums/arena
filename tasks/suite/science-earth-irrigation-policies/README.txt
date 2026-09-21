# Earth science: Water-efficient irrigation policies

**Source collection:** [Earth and environmental science: source-based research tasks](../../papers/science-earth_expansion.md)\
**Task id:** `science-earth-irrigation-policies`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Water-efficient irrigation policies with an explicit candidate interface, physical units, independent evaluator and source-traceable observations or numerical model.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

irrigate(observed_weather_history, soil_state, crop_stage, remaining_water) -> irrigation mm. AquaCrop-OSPy3.0.12 wheat on Tunis1981/82,1983/84,1985/86 and SandyLoam/ClayLoam. API reveals only past weather and current soil; daily<=25mm, seasonal<=150mm. Maximize mean simulated dry yield tonnes/ha; independent simulator tracks actual water. No salinity/fertility/weed stress or measured field-benefit claim.

## Labels

Scientific contribution: `method` (tier 2); artifact `policy`, domain `natural_science`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `earth_and_environment`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Choose irrigation timing and amounts that sustain wheat yield while conserving water.

Why it matters: Water-efficient crop management addresses the competition between agricultural production and limited water resources.

- [AquaCrop modeling to explore optimal irrigation of winter wheat for improving grain yield and water productivity](https://www.sciencedirect.com/science/article/pii/S0378377422001275): Main research objective: Determine winter-wheat irrigation schedules that improve grain yield and water productivity under varying weather conditions. Task connection: The paper directly optimizes wheat irrigation using AquaCrop and weather records. The local policy problem uses the same crop-model family with Tunis weather and its own water budget; it does not validate regional field recommendations or reproduce the paper's sixty-year study.

The supporting paper's main goal is an agricultural water-management decision, rather than introducing the AquaCrop software.

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
- `py:aquacrop`

## Sources

- paper: https://pure.manchester.ac.uk/ws/files/48339277/AquaCropOS_Foster.pdf (Scientific process, benchmark motivation and evaluation assumptions.)
- repository: https://github.com/aquacropos/aquacrop (Original source data/model; local candidate and evaluator are independently implemented.)
- paper: https://agupubs.onlinelibrary.wiley.com/doi/10.1002/2014WR015620 (Develops irrigation decision models coupling crop response, water availability and economic objectives. The local water-budget policy search uses AquaCrop simulations with its own objective and weather cases.)

## Limitations

- Bounded adaptation; no complete source-paper score reproduction or novel scientific discovery claimed.
- Public evaluation cases are development instances; independent generalization requires frozen candidates and new cases.
- AquaCrop-OSPy3.0.12 and bundled Tunis weather; simulated wheat yield.
