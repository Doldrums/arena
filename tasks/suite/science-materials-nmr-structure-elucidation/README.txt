# NMR molecular structure elucidation

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-nmr-structure-elucidation`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

elucidate(h_spectrum, c_spectrum, metadata, k) -> list of one to k distinct molecular SMILES. Metadata may include formula and target-free candidate_smiles. Score exact RDKit-canonical molecular graph recovery in top five; top1 is diagnostic. Enforce valid connected graph and supplied formula. Stereochemistry is ignored only when source labels do not resolve it. Simulated and experimental source subsets must remain separate.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

elucidate(h_spectrum, c_spectrum, metadata, k) -> list of one to k distinct molecular SMILES. Metadata may include formula and target-free candidate_smiles. Score exact RDKit-canonical molecular graph recovery in top five; top1 is diagnostic. Enforce valid connected graph and supplied formula. Stereochemistry is ignored only when source labels do not resolve it. Simulated and experimental source subsets must remain separate.

Parameters: `{"proposal_id": "C07"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `model`, domain `natural_science`, data `public_benchmark`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `chemistry`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer molecular connectivity from routine one-dimensional NMR spectra.

Why it matters: Chemical structure identification is needed to characterize synthesized or isolated compounds.

- [Accurate and Efficient Structure Elucidation from Routine One-Dimensional NMR Spectra Using Multitask Machine Learning](https://pmc.ncbi.nlm.nih.gov/articles/PMC11613330/): Main research objective: Recover chemical structures from one-dimensional proton and carbon NMR measurements. Task connection: The local task returns ranked molecular graphs from corresponding spectral inputs, separating simulated and experimental subsets. Restricted candidate libraries and top-five graph matching do not establish full stereochemical elucidation or general identification of unknown compounds.

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
- `py:rdkit`
- `file:data/materials-expansion/C07/dataset.json`

## Sources

- paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11613330/ (NMR2Struct structure elucidation; simulated release distinct from experimental validation.)
- repository: https://github.com/MarklandGroup/NMR2Struct (Official inference and preprocessing implementation.)
- benchmark: https://zenodo.org/records/13892026 (Official large spectrum dataset; license and subset provenance must be captured before staging.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Stage licensed NMR2Struct spectrum subset, exact molecular graph labels, scaffold groups and target-free candidate graph library. Full archive is about 30 GB; experimental subset not verified.
