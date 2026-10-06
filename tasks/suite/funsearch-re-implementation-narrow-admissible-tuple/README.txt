# Narrow admissible tuple

**Paper:** Generative Modeling for Mathematical Discovery (https://arxiv.org/pdf/2503.11061)\
**Task id:** `funsearch-re-implementation-narrow-admissible-tuple`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Construct the largest admissible tuple within [0, 5000] by selecting a removed residue class for each prime. This is the fixed-diameter maximization formulation actually benchmarked in paper Table 2.

Benchmark named in the paper: Narrow admissible tuple. Paper metric: admissible_tuple_cardinality_at_fixed_diameter_bound.

## Candidate interface

construct() -> list of distinct integers in [0, n] forming an admissible tuple: for every prime p <= len(tuple) some residue class mod p is missed (FunSearch fixed-diameter formulation). Score: tuple size

Parameters: `{"n": 5000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Locally implemented or adapted evaluator for the cited task or benchmark. Data sources, generated instances, evaluation budgets and protocol differences are specified in the candidate contract, requirements and notes; scores are not automatically comparable with published results.

- The source itself uses a fixed diameter bound n=5000 and maximizes surviving tuple size. The local constructor directly returns integers in[0,5000]; for k distinct values it checks a missing residue for every prime<=k (larger primes cannot be fully occupied). The source instead evolves a prime-residue sieve priority. The mathematical feasible set/size objective are shared but candidate interface and search differ. MCTS-AHD ternary admissible sets are a different task and have been restored separately.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/pdf/2503.11061 (Section 3, Tables 1-3)
- repository: https://github.com/kitft/funsearch/tree/cec37d84b474ea6bbd66f6defad8f5b5758449ff (examples/nat_spec.py)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
- The source itself uses a fixed diameter bound n=5000 and maximizes surviving tuple size. The local constructor directly returns integers in[0,5000]; for k distinct values it checks a missing residue for every prime<=k (larger primes cannot be fully occupied). The source instead evolves a prime-residue sieve priority. The mathematical feasible set/size objective are shared but candidate interface and search differ. MCTS-AHD ternary admissible sets are a different task and have been restored separately.
