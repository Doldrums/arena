# julia_prime_counting

**Paper:** Reward-Free Evolving Agents via Pairwise Validator (https://arxiv.org/pdf/2607.14408)\
**Task id:** `pairwise-validator-julia-prime-counting`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

julia_prime_counting task evaluated in Reward-Free Evolving Agents via Pairwise Validator.

Benchmark named in the paper: ADRS / ShinkaEvolve. Paper metric: upstream task score.

## Candidate interface

A Julia program reading queries from argv[1] and writing prime counts to argv[2]; score = 100 * accuracy - runtime seconds (ShinkaEvolve evaluator)

Parameters: `{"queries": "100 .. 25000"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `numerical_computing`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim ShinkaEvolve evaluator called through a thin wrapper.

- Pairwise Validator evaluates the ShinkaEvolve julia_prime_counting example; the evaluator is that example's, verbatim.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `bin:julia`

## Sources

- paper: https://arxiv.org/pdf/2607.14408 (Section 5.4, Table 5)

## Limitations

- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
