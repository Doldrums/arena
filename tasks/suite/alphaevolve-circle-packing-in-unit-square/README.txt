# Circle packing in unit square

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Paper:** AdaEvolve: Adaptive LLM Driven Zeroth-Order Optimization (https://arxiv.org/pdf/2602.20133)\
**Paper:** Harnessing Agentic Evolution (https://arxiv.org/pdf/2605.13821)\
**Paper:** Agentic Optimization: A Framework for Autonomous Coding-Agent Search (https://junye-pan.github.io/posts/agentic-optimization/assets/report.pdf)\
**Paper:** Compute Allocation in Evolutionary Search: From Depth–Breadth to Multi-Armed Bandits (https://arxiv.org/pdf/2605.29268)\
**Paper:** CodeEvolve: an open-source evolutionary framework for algorithmic discovery and optimization (https://arxiv.org/pdf/2510.14150)\
**Paper:** CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery (https://arxiv.org/pdf/2604.01658)\
**Paper:** EurekAgent: Agent Environment Engineering is All You Need For Autonomous Scientific Discovery (https://arxiv.org/pdf/2606.13662)\
**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Paper:** LoongFlow: Directed Evolutionary Search via a Cognitive Plan-Execute-Summarize Paradigm (https://arxiv.org/pdf/2512.24077)\
**Paper:** Reward-Free Evolving Agents via Pairwise Validator (https://arxiv.org/pdf/2607.14408)\
**Paper:** ShinkaEvolve: Towards Open-Ended And Sample-Efficient Program Evolution (https://arxiv.org/pdf/2509.19349)\
**Paper:** The Station: An Open-World Environment for AI-Driven Discovery (https://arxiv.org/pdf/2511.06309)\
**Task id:** `alphaevolve-circle-packing-in-unit-square`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Pack 26 circles with disjoint interiors inside [0,1]^2 and maximize the sum of their radii.

Benchmark named in the paper: Circle packing in unit square. Paper metric: sum of circle radii.

## Candidate interface

construct() -> array of shape (n, 3): rows (x, y, radius) of n disjoint circles inside the unit square

Parameters: `{"n": 26, "published": 2.6358627564136983}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate alphaevolve-circle-packing-in-unit-square --route upstream --paper <paper>`.

- AdaEvolve: Circle packing square 26 (`adaevolve-circle-packing-square-26`; AlphaEvolve math)
- AEvo: Circle packing 26 (`aevo-circle-packing-26`; Circle packing 26)
- Agentic Optimization: Circle packing 26 (`agentic-optimization-circle-packing-26`)
- BaSE: Circle packing 26 (`base-circle-packing-26`; OpenEvolve math)
- CodeEvolve: Circle packing square 26 (`codeevolve-circle-packing-square-26`; AlphaEvolve math)
- CORAL: Circle packing 26 (`coral-circle-packing-26`)
- EurekAgent: Circle packing 26 (`eurekagent-circle-packing-26`)
- EvoX: Circle packing square 26 (`evox-circle-packing-square-26`; AlphaEvolve math)
- LoongFlow: Circle packing square (`loongflow-circle-packing-square`; Circle packing square)
- Pairwise Validator: circle_packing (`pairwise-validator-circle-packing`; ADRS / ShinkaEvolve)
- AdaEvolve, ShinkaEvolve, Agentic Optimization: Circle packing: 26 circles (`reference-circle-packing-26`; Generated locally with documented seed.)
- ShinkaEvolve: Circle packing n=26 (`shinkaevolve-circle-packing-n-26`; Circle packing n=26, 26 circles in unit square)
- The Station: Circle packing n=26 (`the-station-circle-packing-n-26`; Circle packing n=26, Circle packing n=26)

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
- paper: https://arxiv.org/pdf/2602.20133 (Math results and task-definition appendix)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0 (benchmarks/math/circle_packing)
- paper: https://arxiv.org/pdf/2605.13821 (Section 5.1; Appendix C.1)
- paper: https://junye-pan.github.io/posts/agentic-optimization/assets/report.pdf (Report Section 5.1)
- repository: https://github.com/Junye-Pan/AgenticOptimization/tree/712b2fd4888c4b57fc08c1d2bdf4b1ca4c4517fb (tasks/circle_packing_26)
- paper: https://arxiv.org/pdf/2605.29268 (Section 4)
- repository: https://github.com/keruiwu/self-evolving-allocation/tree/ae7b5da1db39c0fd826adda7893c99d5bda5ac1b (tasks/circle_packing)
- paper: https://arxiv.org/pdf/2510.14150 (Appendix A.1)
- repository: https://github.com/inter-co/science-codeevolve/tree/c077959e1ab24b060aaa6d4c563bca2e9cbe8617 (problems/alphaevolve_math_problems/packing_problems/circle_packing_square/26/input)
- paper: https://arxiv.org/pdf/2604.01658 (Section 4.1, Table 1)
- repository: https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408 (examples/math/circle_packing)
- paper: https://arxiv.org/pdf/2606.13662 (Sections 4.1–4.2)
- repository: https://github.com/THU-Team-Eureka/EurekAgent/blob/fb96df897dfb99797a77623aa0dd9ee178fe89d2/examples/circle_packing/SUBMISSION_FORMAT.md (Exact JSON submission contract used for recovered seed)
- repository: https://github.com/THU-Team-Eureka/EurekAgent/tree/fb96df897dfb99797a77623aa0dd9ee178fe89d2 (examples/circle_packing)
- paper: https://arxiv.org/pdf/2602.23413 (Math results and task-definition appendix)
- paper: https://arxiv.org/pdf/2512.24077 (Table 1)
- repository: https://github.com/baidu-baige/LoongFlow/tree/945c78bc1554f8281aac40320b3599bd68d528d7 (agents/math_agent/examples/packing_circle_in_unit_square/eval_program.py)
- paper: https://arxiv.org/pdf/2607.14408 (Section 5.4, Table 5)
- paper: https://arxiv.org/pdf/2509.19349 (Problem family; original benchmark protocol is not claimed.)
- repository: https://github.com/SakanaAI/ShinkaEvolve/tree/9912af12d423504b8d580f4179fd15f5f88b8c50 (examples/circle_packing/evaluate.py)
- paper: https://arxiv.org/pdf/2511.06309 (Section 3.1)
- repository: https://github.com/dualverse-ai/station/tree/782088e561998bf357d95a838a0566a8229425d9 (example/research_alpha_evolve/circle_n26)

## Limitations

- Paper reports over 50 mathematical problems but explicitly details 13 families in Appendix B. Unpublished full task inventory and internal Google assets prevent a complete runnable reproduction.
- Official result notebook provides mathematical constructions and verification, but no AlphaEvolve search implementation. It publishes a subset of all evaluated problems; the full >50 mathematical problem inventory is not disclosed.
- Paper Appendix B.3 writes max(abs(autoconvolution)); notebook B.3 reported 1.4557 construction computes abs(max(autoconvolution)). The notebook separately verifies the max(abs(...)) variant at 1.4688. These are not interchangeable metrics.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
