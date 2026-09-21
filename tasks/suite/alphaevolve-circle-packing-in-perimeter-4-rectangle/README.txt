# Circle packing in perimeter-4 rectangle

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Paper:** AdaEvolve: Adaptive LLM Driven Zeroth-Order Optimization (https://arxiv.org/pdf/2602.20133)\
**Paper:** CodeEvolve: an open-source evolutionary framework for algorithmic discovery and optimization (https://arxiv.org/pdf/2510.14150)\
**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Paper:** LoongFlow: Directed Evolutionary Search via a Cognitive Plan-Execute-Summarize Paradigm (https://arxiv.org/pdf/2512.24077)\
**Task id:** `alphaevolve-circle-packing-in-perimeter-4-rectangle`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Pack 21 circles with disjoint interiors in a variable rectangle of perimeter 4 and maximize the sum of their radii.

Benchmark named in the paper: Circle packing in perimeter-4 rectangle. Paper metric: sum of circle radii.

## Candidate interface

construct() -> array of shape (n, 3): n disjoint circles whose bounding rectangle has perimeter at most 4

Parameters: `{"n": 21, "published": 2.3658321334167627}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate alphaevolve-circle-packing-in-perimeter-4-rectangle --route upstream --paper <paper>`.

- AdaEvolve: Circle packing rectangle 21 (`adaevolve-circle-packing-rectangle-21`; AlphaEvolve math)
- CodeEvolve: Circle packing rectangle 21 (`codeevolve-circle-packing-rectangle-21`; AlphaEvolve math)
- EvoX: Circle packing rectangle 21 (`evox-circle-packing-rectangle-21`; AlphaEvolve math)
- LoongFlow: Circle packing rectangle (`loongflow-circle-packing-rectangle`; Circle packing rectangle)

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

- paper: https://arxiv.org/pdf/2506.13131 (Appendix B.13)
- repository: https://github.com/google-deepmind/alphaevolve_results/tree/4226acbf237ff9ad10ba7673a2af127a2d8a5971 (mathematical_results.ipynb)
- paper: https://arxiv.org/pdf/2602.20133 (Math results and task-definition appendix)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0 (benchmarks/math/circle_packing_rect)
- paper: https://arxiv.org/pdf/2510.14150 (Appendix A.1)
- repository: https://github.com/inter-co/science-codeevolve/tree/c077959e1ab24b060aaa6d4c563bca2e9cbe8617 (problems/alphaevolve_math_problems/packing_problems/circle_packing_rect/input)
- paper: https://arxiv.org/pdf/2602.23413 (Math results and task-definition appendix)
- paper: https://arxiv.org/pdf/2512.24077 (Table 1)
- repository: https://github.com/baidu-baige/LoongFlow/tree/945c78bc1554f8281aac40320b3599bd68d528d7 (agents/math_agent/examples/packing_circle_in_rectangle/eval_program.py)

## Limitations

- Paper reports over 50 mathematical problems but explicitly details 13 families in Appendix B. Unpublished full task inventory and internal Google assets prevent a complete runnable reproduction.
- Official result notebook provides mathematical constructions and verification, but no AlphaEvolve search implementation. It publishes a subset of all evaluated problems; the full >50 mathematical problem inventory is not disclosed.
- Paper Appendix B.3 writes max(abs(autoconvolution)); notebook B.3 reported 1.4557 construction computes abs(max(autoconvolution)). The notebook separately verifies the max(abs(...)) variant at 1.4688. These are not interchangeable metrics.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
