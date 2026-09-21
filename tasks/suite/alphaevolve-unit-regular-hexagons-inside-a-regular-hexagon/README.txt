# Unit regular hexagons inside a regular hexagon

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Paper:** CodeEvolve: an open-source evolutionary framework for algorithmic discovery and optimization (https://arxiv.org/pdf/2510.14150)\
**Paper:** LoongFlow: Directed Evolutionary Search via a Cognitive Plan-Execute-Summarize Paradigm (https://arxiv.org/pdf/2512.24077)\
**Task id:** `alphaevolve-unit-regular-hexagons-inside-a-regular-hexagon`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Place disjoint regular hexagons of side length 1 inside a regular hexagon, minimizing the outer side length; each inner hexagon may translate and rotate.

Benchmark named in the paper: Unit regular hexagons inside a regular hexagon. Paper metric: outer regular hexagon side length.

## Candidate interface

construct() -> (inner, center, side, angle): inner rows (x, y, angle_degrees) of n unit hexagons; outer hexagon center (x, y), side length and rotation; score is the outer side length

Parameters: `{"n": 11, "published": 3.930092}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate alphaevolve-unit-regular-hexagons-inside-a-regular-hexagon --route upstream --paper <paper>`.

- CodeEvolve: Hexagon packing 11 (`codeevolve-hexagon-packing-11`; AlphaEvolve math)
- LoongFlow: Hexagon packing (`loongflow-hexagon-packing`; Hexagon packing)

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

- paper: https://arxiv.org/pdf/2506.13131 (Appendix B.7)
- repository: https://github.com/google-deepmind/alphaevolve_results/tree/4226acbf237ff9ad10ba7673a2af127a2d8a5971 (mathematical_results.ipynb)
- paper: https://arxiv.org/pdf/2510.14150 (Appendix A.1)
- repository: https://github.com/inter-co/science-codeevolve/tree/c077959e1ab24b060aaa6d4c563bca2e9cbe8617 (problems/alphaevolve_math_problems/packing_problems/hexagon_packing/11/input)
- paper: https://arxiv.org/pdf/2512.24077 (Table 1)
- repository: https://github.com/baidu-baige/LoongFlow/tree/945c78bc1554f8281aac40320b3599bd68d528d7 (agents/math_agent/examples/packing_hexagons_in_hexagons/eval_program.py)

## Limitations

- Paper reports over 50 mathematical problems but explicitly details 13 families in Appendix B. Unpublished full task inventory and internal Google assets prevent a complete runnable reproduction.
- Official result notebook provides mathematical constructions and verification, but no AlphaEvolve search implementation. It publishes a subset of all evaluated problems; the full >50 mathematical problem inventory is not disclosed.
- Paper Appendix B.3 writes max(abs(autoconvolution)); notebook B.3 reported 1.4557 construction computes abs(max(autoconvolution)). The notebook separately verifies the max(abs(...)) variant at 1.4688. These are not interchangeable metrics.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
