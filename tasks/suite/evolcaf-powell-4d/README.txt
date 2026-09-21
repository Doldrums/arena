# Powell 4D

**Paper:** Evolve Cost-aware Acquisition Functions Using Large Language Models (https://arxiv.org/pdf/2404.16906)\
**Task id:** `evolcaf-powell-4d`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Powell 4D: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: cost-aware synthetic black-box optimization. Paper metric: optimality gap under cost budget.

## Candidate interface

acquisition(mu, sigma, f_best, cost) -> one score per candidate point; the loop stops when accumulated cost exceeds the budget (EvolCAF-style; cost(x) = 1 + mean normalized coordinate, a documented stand-in for the paper's cost functions). Score: mean simple regret

Parameters: `{"function": "powell_4d", "budget": 30}`

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

- paper: https://arxiv.org/pdf/2404.16906 (Section 4.3 Table 1)
- repository: https://github.com/FeiLiu36/EoH/tree/472545785c936dcfc863d2bc0d6109cf23c7ce62

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- The paper links examples/user_bo_caf in EoH, which is absent from the current pinned tree. New examples/bo_acquisition is not assumed equivalent to the original cost-aware task suite.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
