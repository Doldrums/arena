# Biology: Spatial transcriptomic cell abundance inference

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-spatial-deconvolution`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Infer nonnegative spatial cell counts from reference expression signatures and evaluate separate held-out genes using a count likelihood.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

deconvolve(spatial_counts, reference_profiles, coordinates) -> nonnegative spots x cell_types absolute abundances. Inputs include training genes only and calibrated per-cell signatures. Minimize Poisson NLL of separate held-out genes, using trusted full reference profiles. Known constructed-mixture composition is diagnostic only.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer the cellular composition of tissue locations from spatial transcriptomic counts.

Why it matters: Mapping cell types in tissue helps investigate tissue organization and interactions between cellular populations.

- [Cell2location maps fine-grained cell types in spatial transcriptomics](https://www.nature.com/articles/s41587-021-01139-4): Main research objective: Resolve spatial locations and abundance of fine-grained cell types by combining reference single-cell signatures with spatial transcriptomics. Task connection: The local nonnegative cell-count deconvolution and held-out-gene likelihood preserve this inference target. They do not reproduce the full cell2location hierarchy or establish that inferred cell counts are experimentally correct.

The cited primary paper develops or applies a solution to the stated scientific problem; its task is not merely an agent or general-purpose framework evaluation. Support concerns the scientific problem family, not a claim of new discovery or full-paper reproduction by this local task.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independently written bounded scientific adaptation. Source data and SHA256 preparation receipts required. See docs/BIOLOGY_EXPANSION.md and task limitations; fixture tests never establish source benchmark reproduction.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:../../.cache/science-biology/B06.json`
- `file:../../.cache/science-biology/B06.manifest.json`

## Sources

- paper: https://www.nature.com/articles/s41587-021-01139-4 (cell2location Methods: reference signatures, spatial count decomposition and constructed-mixture validation.)
- repository: https://github.com/vitkl/cell2location_paper (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- Fixed absolute-scale signatures and local Poisson likelihood are a reduced adaptation; full cell2location accounts for additional technical variation. Real-tissue abundance truth is not assumed.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
