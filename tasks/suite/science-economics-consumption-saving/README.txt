# Economics: Consumption-saving policy accuracy

**Source collection:** [Economics and quantitative finance: source-based research tasks](../../papers/science-economics_expansion.md)\
**Task id:** `science-economics-consumption-saving`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Consumption-saving policy accuracy with an explicit candidate API, independently recomputed objective and fixed model/data assumptions.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

solve_consumption(model, resource_grid, budget) -> consumption[t,income_state,resource_index]. Six periods, two Markov income states, CRRA utility, no borrowing. Terminal consumption equals resources. Score independently recomputed mean normalized one-step Bellman improvement on finer off-grid states. The truncated-grid finite-horizon model is declared; no infinite-horizon or empirical-household claim.

## Labels

Scientific contribution: `method` (tier 2); artifact `policy`, domain `finance`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `finance`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine optimal household consumption and saving when future income is uncertain.

Why it matters: Explaining precautionary saving and consumption patterns under income uncertainty is the paper's primary economic question.

- [Buffer-Stock Saving and the Life Cycle/Permanent Income Hypothesis](https://www.nber.org/papers/w5788): Main research objective: Explain household consumption and wealth patterns using a buffer-stock saving model with uncertain income. Task connection: The local task solves a six-period consumption-saving policy problem and measures decision residuals. This short numerical model is a restricted version of the policy problem and does not reproduce the paper's empirical explanations or full life-cycle analysis.

The evidence is a paper whose target is household saving behaviour, rather than relying only on a numerical-method or software citation.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Candidate outputs are independently re-evaluated. Baselines may call named public numerical helpers, but cannot supply their own objective. These bounded research-model adaptations do not establish empirical economic predictions or trading returns.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://www.nber.org/papers/t0309 (Carroll endogenous-grid paper: household budget, income uncertainty and policy solution.)
- repository: https://github.com/econ-ark/HARK (Reference algorithms and source documentation; local evaluator is independently authored.)

## Limitations

- Bounded adaptation specified in the candidate contract; no claim to reproduce full-paper scores.
- Model/simulation scores do not establish empirical policy validity or market returns.
- Public fixed evaluation inputs support development only; freeze candidates and run new cases for generalization.
