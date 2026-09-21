# Climate dynamics: unresolved-tendency closure

**Source collection:** [Climate dynamics: source-based research tasks](../../papers/science-climate.md)\
**Task id:** `science-climate-lorenz96-subgrid-closure`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Fit a shared degree-five polynomial approximation to the unresolved fast-scale forcing of a two-scale Lorenz-96 model. Train on supplied slow-state/tendency pairs and minimize normalized error on independent validation trajectories, including an unseen forcing regime.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct(training_x, training_subgrid_tendency) -> 6 finite real polynomial coefficients in ASCENDING powers of local slow state x, approximating the unresolved tendency as sum(c_i*x**i). Inputs are flattened paired samples from two independent spun-up trajectories at F=6,8. Reference uses Rasp (2020) two-scale Lorenz-96 with K=8,J=4,h=1,c=10,b=10: dX=advection-X+F-h*c*mean(Y); dY=c*(-b*Y_(j+1)*(Y_(j+2)-Y_(j-1))-Y+h*X/J). Fast indices form one periodic K*J ring, crossing slow-cell boundaries. Score is mean validation MSE/variance(true tendency) over three independent trajectories at F=6,8,10. Units nondimensional. Coefficients must be a single shared polynomial for every cell and forcing.

## Labels

Scientific contribution: `method` (tier 2); artifact `equation`, domain `natural_science`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `climate_dynamics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Approximate unresolved forcing in a reduced two-scale Lorenz-96 system.

Why it matters: Physical subgrid modeling is relevant to climate science; this does not make every offline polynomial toy closure a climate-science result.


The cited coupled-training paper demonstrates a learning approach using Lorenz-96. The local degree-five polynomial, reduced dimensions and offline tendency error do not address a demonstrated physical climate question, and no qualifying primary-problem paper was established for this adaptation. No qualifying primary-goal evidence is established for this local task in this review; this is not a finding that the broader subject is unimportant.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Uses the equations and closure target of Rasp (2020), Eqs. (2)-(3), with a locally chosen degree-five deterministic polynomial family and reduced dimensions. Training seeds 31,43 and validation seeds 107,211,307 are disjoint; validation includes a new forcing F=10. Offline tendency error alone does not establish stable online climate forecasts or reproduce the paper's coupled neural-network training.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://gmd.copernicus.org/articles/13/2185/2020/ (Rasp (2020), Section 4.1 Eqs. (2)-(3), slow/fast model and closure target; Section 2 discusses offline versus online evaluation.)

## Limitations

- Local polynomial/offline adaptation with reduced K=8,J=4; not the paper's neural-network coupled-training protocol or a score reproduction.
- Training and validation trajectories use distinct initial seeds; F=10 is absent from training, but all generators are public.
- A deterministic local polynomial cannot recover every fast-scale tendency from the slow scalar alone. Lower offline error does not establish stable coupled forecasts or resolve cloud-feedback uncertainty.
