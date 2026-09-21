# OC20-Dense catalyst adsorption-site search

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-oc20-adsorption-search`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

choose_configuration(surface, adsorbate, configurations, observations) -> unused integer configuration index. Observations reveal index, DFT energy_ev and physically_valid after each query. Score fraction of unseen adsorbate/surface groups finding a physically valid configuration within 0.1 eV of the finite OC20-Dense pool minimum after at most ten queries. Candidate may not introduce unvalidated coordinates.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

choose_configuration(surface, adsorbate, configurations, observations) -> unused integer configuration index. Observations reveal index, DFT energy_ev and physically_valid after each query. Score fraction of unseen adsorbate/surface groups finding a physically valid configuration within 0.1 eV of the finite OC20-Dense pool minimum after at most ten queries. Candidate may not introduce unvalidated coordinates.

Parameters: `{"proposal_id": "C04", "data_sha256": "ecf3b4b78cfb13c2c33f8dff68f6ce382515bd5c18fa02e680eb8588e1572127"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `public_benchmark`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `materials_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find low-energy adsorbate configurations on catalytic surfaces.

Why it matters: Adsorption energies and geometries are central quantities for modeling catalytic reactions.

- [AdsorbML: A Leap in Efficiency for Adsorption Energy Calculations using Generalizable Machine Learning Potentials](https://arxiv.org/abs/2211.16486): Main research objective: Find low-energy adsorbate-surface structures while reducing expensive first-principles relaxation calculations. Task connection: The local task chooses among a finite OC20-Dense pool with ten energy queries. It preserves the adsorption-minimum target but omits free geometry generation/relaxation and measures distance to the pool minimum, not a proven global surface minimum.

The paper's central objective is efficient physical adsorption-energy calculation. Its supporting benchmark is not the sole basis for classification.

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
- `file:data/materials-expansion/C04/dataset.json`

## Sources

- paper: https://arxiv.org/abs/2211.16486 (AdsorbML adsorption-energy landscape search and DFT validation.)
- benchmark: https://opencatalystproject.org/challenge.html (Official OC20-Dense downloads and desorption/dissociation/surface-mismatch validity criteria.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Finite-pool metadata replay uses author-filtered DFT-converged valid configurations and adsorption-site metadata; it does not run relaxations or newly validate atomic geometries. No new geometry is accepted.
