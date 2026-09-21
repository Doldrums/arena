# ODE solver: Heat2D 10x10

**Paper:** DGA2D: Directed Graph-Guided Automated Algorithm Design with Large Language Models (https://arxiv.org/pdf/2608.00700)\
**Task id:** `dga2d-ode-solver-heat2d-10x10`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

ODE solver: Heat2D 10x10

## Candidate interface

integrate(f, t_span, y0) -> y(t_end) for an initial-value problem y' = f(t, y); the evaluator counts calls to f. Score: -log10(relative error) - 0.5 * log10(evaluations)

Parameters: `{"problem": "heat2d_10x10"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `numerical_computing`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Compute accurate initial-value trajectories for spatially discretized heat diffusion in two dimensions with controlled numerical cost.

Why it matters: Stable and efficient integration is needed to simulate spatially discretized heat diffusion in two dimensions. This local model is an idealized numerical-method instance; it does not supply empirical measurements or establish a new physical law.

- [Automatic Selection of Methods for Solving Stiff and Nonstiff Systems of Ordinary Differential Equations](https://doi.org/10.1137/0904010): Main research objective: Improve the efficiency and reliability of solving stiff and nonstiff ordinary differential-equation initial-value systems. Task connection: Petzold develops a numerical integrator that changes methods according to stiffness to solve initial-value systems efficiently. This task implements the same numerical-solution objective for spatially discretized heat diffusion in two dimensions, with a local error-versus-evaluation-cost score and discretization.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/pdf/2608.00700 (Appendix G.1)

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- Paper says an anonymized implementation was supplied as supplementary material but no public URL was found in the extracted PDF.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
