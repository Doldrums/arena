# Experimental surface-code logical decoding

**Source collection:** [Physics and astrophysics research: source-based research tasks](../../papers/science-physics_expansion.md)\
**Task id:** `science-physics-experimental-surface-code`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

decode(detector_events, metadata) -> shot x observable bits. Metadata includes source detector-error model, code distance and observable count. Train/test acquisition batches disjoint. Score logical failure per complete experimental shot, with Wilson confidence interval and timing. PyMatching baseline uses only error model and detector events.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

decode(detector_events, metadata) -> shot x observable bits. Metadata includes source detector-error model, code distance and observable count. Train/test acquisition batches disjoint. Score logical failure per complete experimental shot, with Wilson confidence interval and timing. PyMatching baseline uses only error model and detector events.

Parameters: `{"proposal_id": "P03"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `natural_science`, data `real_measurements`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `quantum_information`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Decode measured surface-code syndromes to reduce logical errors in quantum memories.

Why it matters: Inferring logical corrections from noisy experimental syndromes is the direct error-correction problem addressed by the paper.

- [Learning high-accuracy error decoding for quantum processors](https://www.nature.com/articles/s41586-024-08148-8): Main research objective: Improve surface-code decoding accuracy on experimental quantum-processor data and realistic simulations. Task connection: The local task predicts logical outcomes from complete experimental syndrome shots. Its three X-basis acquisitions and shot-level score are a restricted local evaluation, not the paper's complete decoder architecture or experimental programme.

The paper attempts to solve physical error decoding; its learned architecture is the means of solving that problem.

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
- `file:../../.cache/physics-env/bin/python`
- `file:data/physics-expansion/P03/manifest.json`
- `file:data/physics-expansion/P03/benchmark.npz`

## Sources

- paper: https://www.nature.com/articles/s41586-024-08449-y (Scientific problem, assumptions and evaluation methodology: Experimental surface-code logical decoding)
- archive: https://zenodo.org/records/13273331 (google_105Q_surface_code_d3_d5_d7.zip: experimental detection events, acquisition batches and detector-error model.)

## Limitations

- Independent SCIEL adaptation, not a reproduction of source leaderboard scores.
- Candidate and evaluator share a Python process. Input APIs withhold labels but do not provide an OS security boundary; isolate evaluation data for adversarial use.
- Compact zero-shot experimental pilot: three complete X-basis 13-cycle acquisitions, no fitted training shots and no logical-per-cycle scaling claim.
