# Biology: Single-cell batch integration: public scIB adaptation

**Paper:** The Station: An Open-World Environment for AI-Driven Discovery (https://arxiv.org/pdf/2511.06309)\
**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `the-station-single-cell-batch-integration`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Integrate measured count matrices across experimental batches while preserving cell-type neighborhoods and rare populations under a declared transductive protocol.

Benchmark named in the paper: Biology: Single-cell batch integration: public scIB adaptation. Paper metric: Local protocol; see candidate contract and source adaptation notes.

## Candidate interface

integrate(counts, batch_labels) -> finite cells x dimensions embedding, 1<=dimensions<=128. No cell-type labels supplied. Transductive evaluation. Local scIB-inspired score =0.6 cell-type-macro kNN purity +0.4 within-cell-type batch mixing. Rare-type purity diagnostic. This is an adapted public scIB protocol, not reproduction of Station private scores.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Separate cell identity from experimental batch effects in single-cell expression measurements.

Why it matters: Reliable integration allows biological cell populations to be compared across studies without confusing technical differences with cell biology.

- [Fast, sensitive, and accurate integration of single cell data with Harmony](https://pmc.ncbi.nlm.nih.gov/articles/PMC6884693/): Main research objective: Integrate single-cell data while retaining biological cell-type structure and accounting for experimental differences. Task connection: Harmony directly addresses cross-batch cell-state integration, including pancreatic-islet studies. The local transductive pancreas task measures batch mixing and preservation of annotated neighborhoods; it does not independently discover or validate new cell types.

Harmony is accepted for its domain-specific biological integration objective and applications; the scIB benchmark paper alone is insufficient.

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
- `file:../../.cache/science-biology/B04.json`
- `file:../../.cache/science-biology/B04.manifest.json`

## Sources

- paper: https://arxiv.org/pdf/2511.06309 (Sections 3.2–3.5 and Appendix B)
- repository: https://github.com/dualverse-ai/station/tree/782088e561998bf357d95a838a0566a8229425d9 (example/research_misc/batch_integration)
- paper: https://www.nature.com/articles/s41592-021-01336-8 (scIB Methods: joint evaluation of biological conservation and batch correction.)
- repository: https://github.com/theislab/scib (Official author implementation/data reference; evaluator and seed are independently written, not copied.)
- benchmark: https://ndownloader.figshare.com/files/24539828 (Original scIB pancreas h5ad; rawcounts and genuine technology/cell-type annotations. Pinned SHA256 in data/science/biology_expansion/sources.json.)

## Limitations

- Measured scIB human-pancreas study:1000 hash-selected cells and500variable genes from raw-count layer,9genuine technology batches. Transductive local metrics, no fullscIB/Station score reproduction or cross-study claim.
- Canonical Station upgrade using an explicitly adapted public scIB-style60/40 score. Does not reproduce the private Station evaluator or complete scIB metric suite; no trajectory conservation claim.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
