# Erdos minimum overlap

**Paper:** AlphaEvolve: A coding agent for scientific and algorithmic discovery (https://arxiv.org/pdf/2506.13131)\
**Paper:** CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery (https://arxiv.org/pdf/2604.01658)\
**Paper:** EurekAgent: Agent Environment Engineering is All You Need For Autonomous Scientific Discovery (https://arxiv.org/pdf/2606.13662)\
**Paper:** LoongFlow: Directed Evolutionary Search via a Cognitive Plan-Execute-Summarize Paradigm (https://arxiv.org/pdf/2512.24077)\
**Task id:** `alphaevolve-erdos-minimum-overlap`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Choose equal-width step heights h on [0,2], bounded between 0 and 1 with integral 1, to minimize the maximum overlap of h with shifted 1-h.

Benchmark named in the paper: Erdos minimum overlap. Paper metric: 2*max(correlate(h,1-h,full))/N upper bound.

## Candidate interface

construct() -> sequence of step heights in [0, 1] whose sum is exactly len/2; score is the upper bound on C5

Parameters: `{"steps": 100, "published": 0.38092303510845016}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound Erdős' minimum-overlap constant for a set and translations of its complement.

Why it matters: Determining this extremal constant advances a named problem in combinatorial number theory and analysis. The task seeks explicit feasible constructions relevant to its upper bound.

- [Erdős' minimum overlap problem](https://arxiv.org/abs/2201.05704): Main research objective: Improve rigorous bounds on Erdős' minimum-overlap problem. Task connection: White develops a stronger lower bound for the same minimum-overlap constant. The local task instead searches bounded step-function constructions yielding upper bounds; both address the constant itself, and this paper is not claimed to supply the local construction.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate alphaevolve-erdos-minimum-overlap --route upstream --paper <paper>`.

- CORAL: Erdos minimum overlap (`coral-erdos-minimum-overlap`)
- EurekAgent: Erdos minimum overlap (`eurekagent-erdos-minimum-overlap`)
- LoongFlow: Erdos minimum overlap (`loongflow-erdos-minimum-overlap`; Erdos minimum overlap)

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

- paper: https://arxiv.org/pdf/2506.13131 (Appendix B.5)
- repository: https://github.com/google-deepmind/alphaevolve_results/tree/4226acbf237ff9ad10ba7673a2af127a2d8a5971 (mathematical_results.ipynb)
- paper: https://arxiv.org/pdf/2604.01658 (Section 4.1, Table 1)
- repository: https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408 (examples/math/erdos_min_overlap)
- paper: https://arxiv.org/pdf/2606.13662 (Sections 4.1–4.2)
- repository: https://github.com/THU-Team-Eureka/EurekAgent/blob/fb96df897dfb99797a77623aa0dd9ee178fe89d2/examples/erdos_min_overlap/SUBMISSION_FORMAT.md (Exact JSON submission contract used for recovered seed)
- repository: https://github.com/THU-Team-Eureka/EurekAgent/tree/fb96df897dfb99797a77623aa0dd9ee178fe89d2 (examples/erdos_min_overlap)
- paper: https://arxiv.org/pdf/2512.24077 (Table 1)
- repository: https://github.com/baidu-baige/LoongFlow/tree/945c78bc1554f8281aac40320b3599bd68d528d7 (agents/math_agent/examples/minimum_overlap_problem/eval_program.py)

## Limitations

- Paper reports over 50 mathematical problems but explicitly details 13 families in Appendix B. Unpublished full task inventory and internal Google assets prevent a complete runnable reproduction.
- Official result notebook provides mathematical constructions and verification, but no AlphaEvolve search implementation. It publishes a subset of all evaluated problems; the full >50 mathematical problem inventory is not disclosed.
- Paper Appendix B.3 writes max(abs(autoconvolution)); notebook B.3 reported 1.4557 construction computes abs(max(autoconvolution)). The notebook separately verifies the max(abs(...)) variant at 1.4688. These are not interchangeable metrics.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
