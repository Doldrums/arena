# Sums and differences of finite sets

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Task id:** `alphaevolve-sums-and-differences-of-finite-sets`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Construct a finite set U of nonnegative integers containing 0 to maximize the sumset/difference-set exponent lower bound. The paper supplies constructions of size 2003 and 54265.

Benchmark named in the paper: Sums and differences of finite sets. Paper metric: 1 + log(|U-U|/|U+U|)/log(2*max(U)+1) lower bound.

## Candidate interface

construct() -> list of nonnegative integers containing 0; score is the lower bound 1 + log(|U-U|/|U+U|)/log(2 max U + 1) on C6

Parameters: `{"published": 1.1479888965092757}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct integer sets that improve extremal bounds relating sumset and difference-set cardinalities.

Why it matters: These constructions determine limits in additive combinatorics. Their significance is a stronger mathematical inequality or counterexample, rather than a general-purpose model score.

- [Sums and Differences of Finite Sets](https://gyarmatikati.web.elte.hu/publ/sumdiffv.pdf): Main research objective: Establish sharp relationships and constructive bounds for sizes of finite sumsets and difference sets. Task connection: The paper derives the construction exponent 1 + log(|U−U|/|U+U|)/log(2 max U + 1) from a finite nonnegative integer set U containing zero. This is the local construction objective used by Sums and differences of finite sets.

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

- paper: https://arxiv.org/pdf/2506.13131 (Appendix B.6)
- repository: https://github.com/google-deepmind/alphaevolve_results/tree/4226acbf237ff9ad10ba7673a2af127a2d8a5971 (mathematical_results.ipynb)

## Limitations

- Paper reports over 50 mathematical problems but explicitly details 13 families in Appendix B. Unpublished full task inventory and internal Google assets prevent a complete runnable reproduction.
- Official result notebook provides mathematical constructions and verification, but no AlphaEvolve search implementation. It publishes a subset of all evaluated problems; the full >50 mathematical problem inventory is not disclosed.
- Paper Appendix B.3 writes max(abs(autoconvolution)); notebook B.3 reported 1.4557 construction computes abs(max(autoconvolution)). The notebook separately verifies the max(abs(...)) variant at 1.4688. These are not interchangeable metrics.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
