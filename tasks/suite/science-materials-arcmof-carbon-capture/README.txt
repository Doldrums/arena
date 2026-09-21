# ARC-MOF carbon-capture material selection

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-arcmof-carbon-capture`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

select_mofs(descriptors, operating_conditions, observations, budget) -> list of unused integer MOF indices. Observations reveal computed working_capacity_mol_kg and selectivity. One query per call, maximum twenty queries. Score highest observed capacity meeting the operating-condition selectivity constraint divided by the pool optimum. Topology/chemistry groups remain disjoint and target-derived descriptors are forbidden.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

select_mofs(descriptors, operating_conditions, observations, budget) -> list of unused integer MOF indices. Observations reveal computed working_capacity_mol_kg and selectivity. One query per call, maximum twenty queries. Score highest observed capacity meeting the operating-condition selectivity constraint divided by the pool optimum. Topology/chemistry groups remain disjoint and target-derived descriptors are forbidden.

Parameters: `{"proposal_id": "C05", "data_sha256": "ae243392277fbd39df2dc77892743a982075283bacddb79ac914fa268397a0dd"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `public_benchmark`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `materials_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Identify metal-organic frameworks with useful carbon-dioxide separation performance.

Why it matters: Selective CO2 capture materials are candidates for lowering the energy and resource costs of emissions control.

- [Discovering Ultra-Stable Metal–Organic Frameworks for CO2 Capture from A Wet Flue Gas: Integrating Machine Learning and Molecular Simulation](https://pubs.acs.org/doi/abs/10.1021/acs.est.5c00768): Main research objective: Identify stable MOF adsorbents with favorable CO2 capture properties under flue-gas conditions. Task connection: The paper searches ARC-MOF materials for carbon capture. The local finite-pool task optimizes working capacity subject to selectivity under its own operating conditions; it does not test the paper's wet-gas stability claims, full process economics or experimental deployment.

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
- `file:data/materials-expansion/C05/dataset.json`

## Sources

- paper: https://doi.org/10.26434/chemrxiv-2022-mvr06 (ARC-MOF adsorption-ready curated MOF database.)
- benchmark: https://zenodo.org/records/6908728 (Structures, adsorption outputs and chemistry/topology clusters.)
- paper: https://pubs.acs.org/doi/abs/10.1021/acs.est.5c00768 (Screens ARC-MOF materials for carbon capture using learned filtering and molecular simulations. The local dry post-combustion VSA working-capacity replay, selectivity constraint and query budget are narrower and do not reproduce wet-flue-gas stability screening.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Bounded zero-shot post-combustion VSA replay; selectivity>=10 is a local design constraint. No cross-topology or unseen-chemistry transfer claim.
- Only target-free released geometry descriptors are candidate inputs. Source mmol/g working capacity equals mol/kg numerically.
