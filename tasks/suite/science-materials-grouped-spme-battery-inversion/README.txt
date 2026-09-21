# Grouped-SPMe battery electrochemical inversion

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-grouped-spme-battery-inversion`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

infer_parameters(training_protocols, forward_model, bounds, budget) -> dictionary of exactly the grouped physical parameters in bounds. forward_model(parameters, protocol) is an evaluator-owned pinned PyBOP GroupedSPMe solve; at most 100 training calls. Independent held-out whole-SOC impedance and time-domain protocols score mean normalized complex impedance/voltage RMSE. Enforce physical parameter bounds; uncertainty/identifiability is not inferred from a point estimate. The trusted source adapter must be SHA-256 pinned and may not be candidate-supplied.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

infer_parameters(training_protocols, forward_model, bounds, budget) -> dictionary of exactly the grouped physical parameters in bounds. forward_model(parameters, protocol) is an evaluator-owned pinned PyBOP GroupedSPMe solve; at most 100 training calls. Independent held-out whole-SOC impedance and time-domain protocols score mean normalized complex impedance/voltage RMSE. Enforce physical parameter bounds; uncertainty/identifiability is not inferred from a point estimate. The trusted source adapter must be SHA-256 pinned and may not be candidate-supplied.

Parameters: `{"proposal_id": "C12", "data_sha256": "823cc89f631b97949308a1876f8371d0d3593a265ca40b77a93b0517fab2617b"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `materials_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer physical electrochemical battery-model parameters from impedance measurements.

Why it matters: Physical parameters support interpretable predictions of battery response across operating conditions.

- [Physics-based battery model parametrisation from impedance data](https://arxiv.org/abs/2412.10896): Main research objective: Parameterize a physics-based battery model using impedance data and assess resulting behavior predictions. Task connection: The local GroupedSPMe task uses the corresponding parameter-inference formulation with a bounded forward-model budget and withheld SOC/time-domain protocols. A fitted point estimate does not establish parameter identifiability, uncertainty or validity for unrelated cells.

The cited primary paper develops or applies a solution to the stated scientific problem; its task is not merely an agent or general-purpose framework evaluation. Support concerns the scientific problem family, not a claim of new discovery or full-paper reproduction by this local task.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independently implemented SCIEL adaptation. Source bundles are required except the specified PFHub and Cantera simulations; no generated replacement data. See docs/MATERIALS_EXPANSION.md for provenance, exact setup blockers and validation scope.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:data/materials-expansion/C12/dataset.json`
- `file:../../.cache/materials-battery-env/bin/python`
- `file:data/materials-expansion/C12/raw/OCP_LGM50LT.mat`

## Sources

- paper: https://arxiv.org/abs/2412.10896 (Hallemans et al. grouped-SPMe electrochemical impedance parameterization and time-domain validation.)
- repository: https://github.com/Battery-Intelligence-Lab/Hallemans-2025-JES/tree/3308a34396b8b56cd614291dd151c3405577c068 (Pinned Fig10 EIS fitting and Fig11 time-domain validation scripts; uses PyBOP GroupedSPMe, experimental LG M50LT measurements and OCP tables.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Bounded measured-data adaptation with17 frequencies perSOC and first60s of a withheld drive protocol. Uses source author physical mesh; no parameter identifiability or full paper reproduction claim.
- Forward solves use a separate project-local .cache/materials-battery-env environment; shared candidate process receives only the callable physics interface.
