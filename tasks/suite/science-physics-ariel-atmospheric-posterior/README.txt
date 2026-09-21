# Ariel atmospheric posterior retrieval

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-ariel-atmospheric-posterior`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

retrieve(spectrum, uncertainty, planet_metadata) -> 32..4096 integer indices into source TauREx forward grid, with repetition. Metadata carries physical parameters, opacity-pinned spectra and prior bounds. Posterior is a declared discrete-grid adaptation. Score generating-truth CRPS, agreement with released nested-sampling reference posterior and independent spectral predictive likelihood. Split entire planets and atmospheric regimes.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

retrieve(spectrum, uncertainty, planet_metadata) -> 32..4096 integer indices into source TauREx forward grid, with repetition. Metadata carries physical parameters, opacity-pinned spectra and prior bounds. Posterior is a declared discrete-grid adaptation. Score generating-truth CRPS, agreement with released nested-sampling reference posterior and independent spectral predictive likelihood. Split entire planets and atmospheric regimes.

Parameters: `{"proposal_id": "P08"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `simulator`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `cosmology_and_astrophysics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Infer exoplanet atmospheric composition and physical parameters from transmission spectra.

Why it matters: Understanding an exoplanet atmosphere through spectral retrieval is the cited paper's primary scientific goal.

- [Sulfur dioxide in the mid-infrared transmission spectrum of WASP-39b](https://www.nature.com/articles/s41586-024-07040-9): Main research objective: Determine the composition of WASP-39b's atmosphere from its observed mid-infrared transmission spectrum. Task connection: The local Ariel/TauREx task performs posterior inference on a discrete simulated atmospheric grid. It shares the retrieval problem, but has different spectra, species, model assumptions, and posterior restrictions; it neither analyses WASP-39b observations nor reproduces the sulfur-dioxide result.

The evidence is a science paper using retrieval to answer an atmospheric-composition question, rather than only a dataset or retrieval-software paper.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Independent SCIEL scientific adaptation. Required source packs never fall back to toy data. Fixture tests are distinct from source-data execution. See docs/PHYSICS_EXPANSION.md.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`
- `file:data/physics-expansion/P08/manifest.json`
- `file:data/physics-expansion/P08/benchmark.npz`

## Sources

- paper: https://proceedings.mlr.press/v220/yip23a.html (Scientific problem, assumptions and evaluation methodology: Ariel atmospheric posterior retrieval)
- archive: https://zenodo.org/records/6770103 (Level1/Level2 observations and nested-sampling posterior; exact TauREx opacity/model grid must be curated.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Published tutorial opacity grid is R≈1000 versus source-model R=10000; released radius/mass/gravity units require further validation. The independent likelihood has not reproduced source truth, so no successful seed execution is claimed.
