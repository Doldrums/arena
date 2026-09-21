# Matbench DFT-stable crystal screening

**Source collection:** [Chemistry and materials research: source-based research tasks](../../papers/science-materials_expansion.md)\
**Task id:** `science-materials-matbench-stability-screening`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

rank_crystals(unrelaxed_structures, budget) -> exactly budget unique integer indices. Structures are evaluator-provided pre-relaxation crystal records, with optional target-free descriptors; labels remain private. Score precision of DFT energy-above-reference-hull <=0 eV/atom among selected candidates. Training MP and evaluation WBM chemistry/structure groups must be disjoint; no claim of experimental synthesis.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

rank_crystals(unrelaxed_structures, budget) -> exactly budget unique integer indices. Structures are evaluator-provided pre-relaxation crystal records, with optional target-free descriptors; labels remain private. Score precision of DFT energy-above-reference-hull <=0 eV/atom among selected candidates. Training MP and evaluation WBM chemistry/structure groups must be disjoint; no claim of experimental synthesis.

Parameters: `{"proposal_id": "C03", "data_sha256": "1d891953e6101f90076ffeb0c6b3d0f36de0fe84ff2196e5c909d7170fa0dd79"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `public_benchmark`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `materials_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Identify inorganic crystal structures predicted to be thermodynamically stable.

Why it matters: Stable-crystal discovery expands candidates for materials with useful physical properties.

- [Scaling deep learning for materials discovery](https://www.nature.com/articles/s41586-023-06735-9): Main research objective: Discover stable inorganic crystals through learned energy predictions and first-principles validation. Task connection: The local task selects stable candidates from unrelaxed WBM structures using DFT reference-hull labels. It is restricted candidate screening and does not claim discovery of the paper's materials, experimental synthesis, or stability beyond the reference hull.

The evidence is a materials-discovery study, rather than the Matbench Discovery benchmark introduction.

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
- `file:data/materials-expansion/C03/dataset.json`

## Sources

- paper: https://arxiv.org/abs/2308.14920 (Matbench Discovery; stability discovery, MP/WBM split and reference convex hull.)
- repository: https://github.com/janosh/matbench-discovery (Official stability benchmark and data registry.)
- benchmark: https://figshare.com/articles/dataset/Matbench_Discovery_v1_0_0/22715158 (Released structures and DFT reference outcomes.)

## Limitations

- Independent SCIEL adaptation of a cited scientific problem; no claim to reproduce author leaderboard scores.
- Candidate and evaluator run in one Python process; data access is separated by API, not an OS sandbox. Isolate evaluator data for adversarial or held-out evaluation.
- Bounded zero-shot screening adaptation: 512 source WBM geometries in four128-candidate pools, selected by label-independent hash. No MP training data or trained checkpoint is supplied and full Matbench leaderboard performance is not claimed.
