# Circle packing in unit square n=32

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Paper:** CodeEvolve: an open-source evolutionary framework for algorithmic discovery and optimization (https://arxiv.org/pdf/2510.14150)\
**Paper:** The Station: An Open-World Environment for AI-Driven Discovery (https://arxiv.org/pdf/2511.06309)\
**Task id:** `alphaevolve-circle-packing-in-unit-square-n-32`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Pack 32 circles with disjoint interiors inside [0,1]^2 and maximize the sum of their radii.

Benchmark named in the paper: Circle packing in unit square. Paper metric: sum of circle radii.

## Candidate interface

construct() -> array of shape (n, 3): rows (x, y, radius) of n disjoint circles inside the unit square

Parameters: `{"n": 32, "published": 2.937944526205518}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate alphaevolve-circle-packing-in-unit-square-n-32 --route upstream --paper <paper>`.

- CodeEvolve: Circle packing square 32 (`codeevolve-circle-packing-square-32`; AlphaEvolve math)
- CodeEvolve: Circle packing: 32 circles (`reference-circle-packing-32`; Generated locally with documented seed.)
- The Station: Circle packing n=32 (`the-station-circle-packing-n-32`; Circle packing n=32, Circle packing n=32)

## Evaluation protocol

Reimplemented in this repository and cross-checked against the paper's published constructions/values.

- Verification reimplemented from the AlphaEvolve mathematical_results notebook; the published construction reproduces the published value exactly with this evaluator (see tests/test_suite.py).
- Independent implementation of the AlphaEvolve verification; reproduces the notebook's published values exactly.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2506.13131 (Appendix B.12)
- repository: https://github.com/google-deepmind/alphaevolve_results/tree/4226acbf237ff9ad10ba7673a2af127a2d8a5971 (mathematical_results.ipynb)
- paper: https://arxiv.org/pdf/2510.14150 (Appendix A.1)
- repository: https://github.com/inter-co/science-codeevolve/tree/c077959e1ab24b060aaa6d4c563bca2e9cbe8617 (problems/alphaevolve_math_problems/packing_problems/circle_packing_square/32/input)
- paper: https://arxiv.org/pdf/2511.06309 (Section 3.1)
- repository: https://github.com/dualverse-ai/station/tree/782088e561998bf357d95a838a0566a8229425d9 (example/research_alpha_evolve/circle_n32)

## Limitations

- Paper reports over 50 mathematical problems but explicitly details 13 families in Appendix B. Unpublished full task inventory and internal Google assets prevent a complete runnable reproduction.
- Official result notebook provides mathematical constructions and verification, but no AlphaEvolve search implementation. It publishes a subset of all evaluated problems; the full >50 mathematical problem inventory is not disclosed.
- Paper Appendix B.3 writes max(abs(autoconvolution)); notebook B.3 reported 1.4557 construction computes abs(max(autoconvolution)). The notebook separately verifies the max(abs(...)) variant at 1.4688. These are not interchangeable metrics.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
