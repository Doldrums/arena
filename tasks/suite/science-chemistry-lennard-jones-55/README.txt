# Lennard-Jones cluster global minimum, 55 atoms

**Source collection:** [Computational chemistry: source-based research tasks](../../papers/science-chemistry.md)\
**Task id:** `science-chemistry-lennard-jones-55`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Place 55 atoms interacting through the Lennard-Jones potential to minimise the total energy. The global minimum is the complete two-shell Mackay icosahedron (energy -279.248470, Cambridge Cluster Database). The evaluator computes the energy exactly; the seed is a cubic lattice fragment.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> array of shape (N, 3): Cartesian coordinates of N atoms in reduced Lennard-Jones units (sigma = 1). Atoms must be at least 0.5 apart. Score: total Lennard-Jones energy 4*sum(r^-12 - r^-6) over all pairs, minimized. science_chemistry.relax(positions) (L-BFGS local relaxation) is available to candidates.

Parameters: `{"n": 55, "published": -279.24847}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `natural_science`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `chemistry`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the lowest-energy structure of a 55-atom cluster under the Lennard-Jones interaction model.

Why it matters: Finite-cluster ground states reveal how interatomic interactions and geometric packing shape molecular-scale structures.

- [Global Optimization by Basin-Hopping and the Lowest Energy Structures of Lennard-Jones Clusters Containing up to 110 Atoms](https://pubs.acs.org/doi/full/10.1021/jp970984n): Main research objective: Locate low-energy Lennard-Jones cluster structures, including difficult sizes and structures not previously found in unbiased searches. Task connection: The paper explicitly solves Lennard-Jones structural minima for sizes up to 110, including N=55; the local task uses the same physical energy minimization. Reaching the cited known structure is reproduction, and the model is an idealized pair potential rather than a specific experimental material.

This is a physical cluster-structure optimization study with actual structure results, not a citation that merely uses the cluster as an agent benchmark.

## Evaluation protocol

Reimplemented in this repository and cross-checked against the paper's published constructions/values.

- Exact Lennard-Jones energy; the Cambridge Cluster Database minima for 13, 38 and 55 atoms are reproduced in tests/test_science_chemistry.py by constructing the icosahedral and truncated-octahedral geometries and relaxing them locally (agreement to 1e-6).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://doi.org/10.1021/jp970984n (Wales and Doye 1997, basin-hopping global optimisation of Lennard-Jones clusters.)
- benchmark: https://www-wales.ch.cam.ac.uk/CCD.html (Cambridge Cluster Database (LJ table): N=55, point group Ih, energy -279.248470; inspected 2026-09-20.)

## Limitations

- Putative global minimum, reproduced in tests from the Mackay icosahedron construction plus local relaxation.
- Reaching the database value reproduces a known structure; a lower energy would need independent verification.
