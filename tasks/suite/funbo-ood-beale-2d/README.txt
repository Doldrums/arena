# OOD Beale 2D

**Paper:** FunBO: Discovering Acquisition Functions for Bayesian Optimization with FunSearch (https://arxiv.org/pdf/2406.04824)\
**Task id:** `funbo-ood-beale-2d`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

OOD Beale 2D: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: OOD-Bench. Paper metric: simple regret and trials to optimum.

## Candidate interface

acquisition(mu, sigma, f_best) -> one score per candidate point (higher = evaluate next) for a Gaussian-process BO loop on a synthetic function (FunBO contract). Score: mean simple regret after the evaluation budget

Parameters: `{"function": "beale_2d", "budget": 30}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `continuous_optimisation`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

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

- paper: https://arxiv.org/pdf/2406.04824 (Section 4 OOD-Bench and Appendix C.1)
- paper: https://arxiv.org/html/2406.04824v2 (AppendixA Figures8/9; AppendixC.1 Table1)
- repository: https://github.com/boschresearch/MetaBO/blob/3f458bd32db340fbe2d5f072a92cfd782072342c/metabo/environment/objectives.py (Paper-cited comparison repository; objective functions bra,gprice,hm3 (not original FunBO source))
- repository: https://github.com/boschresearch/MetaBO/tree/3f458bd32db340fbe2d5f072a92cfd782072342c (metabo/environment/objectives.py)

## Limitations

- No dedicated official FunBO evaluator repository was verified. The nine OOD adapters are explicitly attributed paper-guided reconstructions using the paper-cited MetaBO objective source.
- Exact original Sobol points and some standard-objective internal parameters are unavailable; assumptions and fingerprints are documented per task.
- No full FunSearch discovery or complete paper experiment has been reproduced.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
