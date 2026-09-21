# Biology: Reference-aware environmental metagenome assembly

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-cami-metagenome-assembly`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Reconstruct microbial contigs from CAMI-derived reads and score genome recovery with independent reference-aware misassembly and sequence-error penalties.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

assemble(reads, library_metadata) -> bounded list of ACGTN contigs. Hidden reference genomes evaluated using metaQUAST 5.3.0. Score genome_fraction/(1+misassemblies+sequence_errors_per_100kb/1000); corrected NA50 diagnostic. metaQUAST and licensed CAMI community data must be staged; no synthetic replacement.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Reconstruct microbial genomes from mixed-community sequencing reads.

Why it matters: Assembly makes microbial genetic content accessible for studying communities that cannot easily be isolated in culture.

- [metaSPAdes: a new versatile metagenomic assembler](https://pmc.ncbi.nlm.nih.gov/articles/PMC5411777/): Main research objective: Assemble metagenomic reads despite uneven species abundance and closely related microbial strains. Task connection: The local CAMI-derived read task performs this reconstruction with reference-aware recovery and misassembly scoring. Simulated community reads and local scoring do not establish performance on arbitrary environmental communities.

The primary paper solves the specific biological sequence-reconstruction problem. The CAMI assessment/dataset paper alone does not qualify.

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
- `file:../../.cache/science-biology/B08.json`
- `file:../../.cache/science-biology/B08.manifest.json`
- `bin:metaquast.py`

## Sources

- paper: https://www.nature.com/articles/s41592-022-01431-4 (CAMI II Methods: simulated community datasets and assembly evaluation.)
- repository: https://github.com/CAMI-challenge/second_challenge_evaluation (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- Requires source CAMI reads/reference genomes and metaQUAST5.3.0. No locally generated substitute is scored as CAMI. Local composite score differs from paper multi-metric ranking; correctedNA50 is diagnostic.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
