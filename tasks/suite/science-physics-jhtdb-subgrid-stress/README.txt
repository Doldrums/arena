# JHTDB turbulent subgrid stress

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-jhtdb-subgrid-stress`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

closure(filtered_velocity, gradients, filter_width) -> N x N x N x 3 x 3 symmetric subgrid stress. Complete periodic source DNS boxes (not wrapped cutouts) supply independent box-filtered ground truth. Whole space-time blocks split. Score stress and energy-transfer errors plus Fourier energy error after evaluator RK2 coarse rollout. Galilean and cyclic rotational consistency and rollout stability required.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

closure(filtered_velocity, gradients, filter_width) -> N x N x N x 3 x 3 symmetric subgrid stress. Complete periodic source DNS boxes (not wrapped cutouts) supply independent box-filtered ground truth. Whole space-time blocks split. Score stress and energy-transfer errors plus Fourier energy error after evaluator RK2 coarse rollout. Galilean and cyclic rotational consistency and rollout stability required.

Parameters: `{"proposal_id": "P11"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `physics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Model unresolved turbulent stresses accurately enough to improve coarse large-eddy simulations.

Why it matters: Obtaining useful turbulent closure terms and stable coarse simulations is the main scientific-computing objective of the paper.

- [Deep Neural Networks for Data-Driven Turbulence Models](https://arxiv.org/abs/1806.04482): Main research objective: Learn closure terms from direct numerical simulation and use them to construct accurate, stable large-eddy simulations. Task connection: The local task predicts subgrid stresses from filtered periodic JHTDB turbulence, with energy-transfer, invariance, and rollout checks. Its flow selection, tensor target, and scoring differ from the published closure construction; JHTDB supplies data rather than the importance evidence.

The source proposes and tests a solution to turbulence closure, not a general-purpose model benchmark.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independent SCIEL scientific adaptation. Required source packs never fall back to toy data. Fixture tests are distinct from source-data execution. See docs/PHYSICS_EXPANSION.md.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:data/physics-expansion/P11/manifest.json`
- `file:data/physics-expansion/P11/benchmark.npz`

## Sources

- paper: https://turbulence.pha.jhu.edu/papers/lietal-jhudatabase2008.pdf (Scientific problem, assumptions and evaluation methodology: JHTDB turbulent subgrid stress)
- archive: https://turbulence.idies.jhu.edu/datasets (Periodic isotropic DNS velocity fields with whole space-time block holdouts; filter and coarse-flow checks.)
- paper: https://arxiv.org/abs/1806.04482 (Learns unresolved closure terms from filtered direct numerical simulations and evaluates stable large-eddy rollouts. The local JHTDB stress-tensor target, invariance checks and numerical rollout are a distinct task-family adaptation.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Acquire complete periodic JHTDB DNS fields at separated times with source viscosity/spacing; no wrapping arbitrary small cutouts.
