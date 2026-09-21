# Kissing number in dimension 11

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Task id:** `alphaevolve-kissing-number-in-dimension-11`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Construct nonzero integer vectors in R^11 whose minimum pairwise distance is at least the maximum vector norm. Normalizing each vector to norm 2 certifies a kissing configuration of equal-radius spheres.

Benchmark named in the paper: Kissing number in dimension 11. Paper metric: number of valid nonzero integer vectors.

## Candidate interface

construct() -> integer array of shape (k, d): nonzero vectors whose minimum pairwise distance is at least the maximum norm; score is k

Parameters: `{"d": 11, "published": 593.0}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct large eleven-dimensional kissing configurations of nonoverlapping spheres.

Why it matters: Kissing configurations establish lower bounds in discrete geometry and are related to spherical codes. Each additional validated sphere can strengthen a mathematical packing bound; the local score is not a general AI benchmark metric.

- [Finding Kissing Numbers with Game-theoretic Reinforcement Learning](https://arxiv.org/abs/2511.13391): Main research objective: Discover sphere configurations giving stronger kissing-number lower bounds. Task connection: The paper directly constructs kissing configurations to improve kissing-number bounds. This local task fixes dimension eleven and restricts its representation; the paper establishes the primary problem pursued, without implying that its reported improvements occur in dimension eleven.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Reimplemented in this repository and cross-checked against the paper's published constructions/values.

- Verification reimplemented from the AlphaEvolve mathematical_results notebook; the published construction reproduces the published value exactly with this evaluator (see tests/test_suite.py).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2506.13131 (Appendix B.11)
- repository: https://github.com/google-deepmind/alphaevolve_results/tree/4226acbf237ff9ad10ba7673a2af127a2d8a5971 (mathematical_results.ipynb)

## Limitations

- Paper reports over 50 mathematical problems but explicitly details 13 families in Appendix B. Unpublished full task inventory and internal Google assets prevent a complete runnable reproduction.
- Official result notebook provides mathematical constructions and verification, but no AlphaEvolve search implementation. It publishes a subset of all evaluated problems; the full >50 mathematical problem inventory is not disclosed.
- Paper Appendix B.3 writes max(abs(autoconvolution)); notebook B.3 reported 1.4557 construction computes abs(max(autoconvolution)). The notebook separately verifies the max(abs(...)) variant at 1.4688. These are not interchangeable metrics.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
