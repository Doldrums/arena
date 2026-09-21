# GEOM molecular conformer ensemble search

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-geom-conformer-search`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

conformers(molecular_graph_smiles, stereochemistry, budget) -> K x N x 3 coordinates in Angstrom, N is RDKit AddHs atom order and 1<=K<=budget. Return bounded physically plausible conformers preserving all explicit stereocentres. Score molecular-macro GEOM heavy-atom symmetry-aware RMSD coverage at 0.5 Angstrom; matching RMSD is diagnostic. Evaluator checks bond distances, clashes and chirality against the molecular graph.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

conformers(molecular_graph_smiles, stereochemistry, budget) -> K x N x 3 coordinates in Angstrom, N is RDKit AddHs atom order and 1<=K<=budget. Return bounded physically plausible conformers preserving all explicit stereocentres. Score molecular-macro GEOM heavy-atom symmetry-aware RMSD coverage at 0.5 Angstrom; matching RMSD is diagnostic. Evaluator checks bond distances, clashes and chirality against the molecular graph.

Parameters: `{"proposal_id": "C02", "data_sha256": "c5c4309e6bdb881b0fc6236a0d0ed4a79f6e8478a07665a3f4d8d21aafc7e141"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `public_benchmark`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `chemistry`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find physically plausible low-energy conformational ensembles of molecules.

Why it matters: Molecular conformations affect spectra, thermodynamic properties and molecular interactions.

- [Automated exploration of the low-energy chemical space with fast quantum chemical methods](https://pubs.rsc.org/en/content/articlehtml/2020/cp/c9cp06869d): Main research objective: Generate quantum-chemically grounded conformer ensembles representing significantly populated molecular structures. Task connection: The local task constructs stereochemistry-preserving conformers and scores coverage of GEOM reference structures. It measures a restricted geometric aspect of conformer search, not thermodynamic populations, spectroscopic accuracy or all CREST procedures.

The paper directly pursues physical molecular-ensemble construction; the GEOM dataset paper by itself is excluded.

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
- `py:rdkit`
- `file:data/materials-expansion/C02/dataset.json`

## Sources

- paper: https://doi.org/10.1038/s41597-022-01288-4 (GEOM conformer ensembles; dataset preparation and molecular diversity evaluation.)
- benchmark: https://github.com/learningmatter-mit/geom (Official conformer pickles and dataset loading instructions; each trusted source pickle must be hash-pinned before conversion.)
- paper: https://arxiv.org/abs/2203.02923 (Generates molecular conformations from molecular graphs and benchmarks conformation quality and coverage. The local GEOM subset, budget, stereochemistry and validity checks are a restricted protocol.)
- archive: https://zenodo.org/records/20633997 (ChoderaLab Modelforge GEOM-QM9 nc_1000_v1.0 curation, CC0; 67 molecules/1000 actual conformers, publisher MD5 and full source SHA256 verified. 57 complete ensembles/958 conformers retained after source-only graph, valence and stereochemistry audit.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Secondary published scientific curation of GEOM-QM9, zero-shot pilot over57 molecules/958 released conformers. No claim to cover the complete original ensemble archive, GEOM-Drugs, or experimental conformer populations.
- Ten entire source ensembles excluded by graph/valence/stereochemistry checks before candidate evaluation. Source atomic order is recovered using geometry-based bond perception and verified chirality-preserving graph isomorphism; all retained reference frames pass the physical contract.
- No fitted training split is used. Coverage measures the released subset only; author-curation selection may differ from the full GEOM population.
