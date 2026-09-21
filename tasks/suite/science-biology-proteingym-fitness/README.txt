# Biology: ProteinGym measured protein variant effects

**Source collection:** [Biology and bioinformatics: source-based research tasks](../../papers/science-biology_expansion.md)\
**Task id:** `science-biology-proteingym-fitness`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Fit a mutation-effect model from measured support substitutions and predict complete held-out mutation positions in three ProteinGym assays.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

fit(reference_sequence, support_variants, support_effects) -> model with score(query_variants) returning one finite value per query. Variants use ProteinGym colon-separated substitutions. Score is equal-assay mean Spearman; frozen complete-position holdout, constant predictions score 0. Query labels never passed to candidate.

## Labels

Scientific contribution: `method` (tier 2); artifact `model`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `biology`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Predict how amino-acid substitutions change protein function.

Why it matters: Mutation-effect prediction helps interpret molecular function and prioritize variants for biological experiments.

- [Tranception: Protein Fitness Prediction with Autoregressive Transformers and Inference-time Retrieval](https://proceedings.mlr.press/v162/notin22a.html): Main research objective: Predict protein fitness from sequence by combining evolutionary retrieval and a protein sequence model. Task connection: The paper directly predicts measured protein mutation effects. The local task fits support mutations and holds out complete positions in three assays; it is a restricted supervised protocol, not the full Tranception experiment or a disease diagnosis.

The primary objective is the domain problem of protein fitness prediction. The accompanying ProteinGym benchmark alone would not establish this evidence.

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
- `file:../../.cache/science-biology/B01.json`
- `file:../../.cache/science-biology/B01.manifest.json`

## Sources

- paper: https://papers.neurips.cc/paper_files/paper/2023/file/cac723e5ff29f65e3fcbb0739ae91bee-Paper-Datasets_and_Benchmarks.pdf (ProteinGym supervised DMS benchmark definition and evaluation; fitness-rank comparisons.)
- repository: https://github.com/OATML-Markslab/ProteinGym (Official author implementation/data reference; evaluator and seed are independently written, not copied.)

## Limitations

- Measured three-assay single-substitution adaptation; does not yet test higher-order epistasis or completely unseen proteins. Equal-assay mean differs from official hierarchical ProteinGym aggregation.
- Public source subsets are development-visible. Freeze candidates before evaluating on additional independently chosen studies/instances; trusted candidate execution is not a security sandbox.
- Improving this benchmark is a scientific-method result; it does not alone establish a new biological discovery.
