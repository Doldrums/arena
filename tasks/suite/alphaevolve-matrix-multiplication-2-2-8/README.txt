# Matrix multiplication 2,2,8

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Task id:** `alphaevolve-matrix-multiplication-2-2-8`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Find a rank-minimal exact tensor decomposition for multiplying a 2 by 2 matrix by a 2 by 8 matrix. The output factor follows the official trace convention W[k*n+i,r].

Benchmark named in the paper: matrix multiplication tensor <2,2,8>. Paper metric: tensor rank.

## Candidate interface

construct() -> {'U', 'V', 'W'}: factor matrices of shapes (n*m, rank), (m*p, rank), (p*n, rank) with integer/half-integer entries that exactly decompose the matrix multiplication tensor; score is the rank

Parameters: `{"dimensions": [2, 2, 8], "coefficient_domain": "real_half_integers", "published": 28}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Find exact low-rank bilinear algorithms with real half-integer coefficients for multiplying 2×2 and 2×8 matrices.

Why it matters: Reducing exact scalar-multiplication complexity advances algebraic complexity and can reduce a core cost of scientific linear algebra. This local task seeks a verifiable tensor decomposition; a lower local rank alone does not prove a faster practical implementation.

- [Discovering faster matrix multiplication algorithms with reinforcement learning](https://doi.org/10.1038/s41586-022-05172-4): Main research objective: Discover and verify more efficient matrix-multiplication algorithms, rather than measure general agent performance. Task connection: The paper searches for exact low-rank matrix-multiplication tensor decompositions over real and finite-field arithmetic. This task uses real half-integer coefficients and fixes dimensions to (2, 2, 8); the citation establishes the primary research problem, not a claim that this exact local coefficient domain or size is a new published result.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Reimplemented in this repository and cross-checked against the paper's published constructions/values.

- Exact verification of the decomposition with integer arithmetic (reimplementation of AlphaEvolve Appendix A); the published rank is the paper's reported rank.
- Exact verification with integer arithmetic (in-repo reimplementation of AlphaEvolve Appendix A).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2506.13131 (Appendix A, Table 3)
- repository: https://github.com/google-deepmind/alphaevolve_results/tree/4226acbf237ff9ad10ba7673a2af127a2d8a5971

## Limitations

- Independent exact task evaluator derived from Appendix A; does not reproduce AlphaEvolve search or its learned constructions.
- Coefficient domain matches reported integer/half-integer (or Gaussian half-integer) representation; it is not unrestricted tensor rank over every scalar field.
