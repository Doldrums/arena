# Maximum-to-minimum distance ratio

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Paper:** Compute Allocation in Evolutionary Search: From Depth–Breadth to Multi-Armed Bandits (https://arxiv.org/pdf/2605.29268)\
**Paper:** CodeEvolve: an open-source evolutionary framework for algorithmic discovery and optimization (https://arxiv.org/pdf/2510.14150)\
**Paper:** CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery (https://arxiv.org/pdf/2604.01658)\
**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Paper:** LoongFlow: Directed Evolutionary Search via a Cognitive Plan-Execute-Summarize Paradigm (https://arxiv.org/pdf/2512.24077)\
**Task id:** `alphaevolve-maximum-to-minimum-distance-ratio`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Place 16 distinct points in two-dimensional Euclidean space to minimize the squared ratio of maximum to minimum pairwise distance.

Benchmark named in the paper: Maximum-to-minimum distance ratio. Paper metric: (maximum pairwise distance / minimum pairwise distance)^2.

## Candidate interface

construct() -> array of shape (n, d): n distinct points; score is (max pairwise distance / min pairwise distance)^2

Parameters: `{"n": 16, "d": 2, "published": 12.88926611203463}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate alphaevolve-maximum-to-minimum-distance-ratio --route upstream --paper <paper>`.

- BaSE: MinMaxDist 16 (`base-minmaxdist-16`; OpenEvolve math)
- CodeEvolve: Min-max distance 16 points 2D (`codeevolve-min-max-distance-16-points-2d`; AlphaEvolve math)
- CORAL: Min-max distance 16 points 2D (`coral-min-max-distance-16-points-2d`)
- EvoX: Min-max distance dimension 2 (`evox-min-max-distance-dimension-2`; AlphaEvolve math, 16 points in dimension 2)
- LoongFlow: Max-to-min ratios (`loongflow-max-to-min-ratios`; Max-to-min ratios)

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

- paper: https://arxiv.org/pdf/2506.13131 (Appendix B.8)
- repository: https://github.com/google-deepmind/alphaevolve_results/tree/4226acbf237ff9ad10ba7673a2af127a2d8a5971 (mathematical_results.ipynb)
- paper: https://arxiv.org/pdf/2605.29268 (Section 4)
- repository: https://github.com/keruiwu/self-evolving-allocation/tree/ae7b5da1db39c0fd826adda7893c99d5bda5ac1b (tasks/min_max_dist)
- paper: https://arxiv.org/pdf/2510.14150 (Appendix A.1)
- repository: https://github.com/inter-co/science-codeevolve/tree/c077959e1ab24b060aaa6d4c563bca2e9cbe8617 (problems/alphaevolve_math_problems/minimizing_max_min_dist/2/input)
- paper: https://arxiv.org/pdf/2604.01658 (Section 4.1, Table 1)
- repository: https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408 (examples/math/minimizing_max_min_dist_2d)
- paper: https://arxiv.org/pdf/2602.23413 (Table 2)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0 (benchmarks/math/minimizing_max_min_dist/2)
- paper: https://arxiv.org/pdf/2512.24077 (Table 1)
- repository: https://github.com/baidu-baige/LoongFlow/tree/945c78bc1554f8281aac40320b3599bd68d528d7 (agents/math_agent/examples/max_to_min_ratios/eval_program.py)

## Limitations

- Paper reports over 50 mathematical problems but explicitly details 13 families in Appendix B. Unpublished full task inventory and internal Google assets prevent a complete runnable reproduction.
- Official result notebook provides mathematical constructions and verification, but no AlphaEvolve search implementation. It publishes a subset of all evaluated problems; the full >50 mathematical problem inventory is not disclosed.
- Paper Appendix B.3 writes max(abs(autoconvolution)); notebook B.3 reported 1.4557 construction computes abs(max(autoconvolution)). The notebook separately verifies the max(abs(...)) variant at 1.4688. These are not interchangeable metrics.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
