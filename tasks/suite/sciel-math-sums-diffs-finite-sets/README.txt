# SCiEL: Finite-set sum and difference ratio

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-math-sums-diffs-finite-sets`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Construct a finite set of integers maximizing the sum/difference inequality constant c6 checked by the evaluator.

Benchmark named in the paper: SCiEL source example sums_diffs_finite_sets. Paper metric: combined_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct integer sets that improve extremal bounds relating sumset and difference-set cardinalities.

Why it matters: These constructions determine limits in additive combinatorics. Their significance is a stronger mathematical inequality or counterexample, rather than a general-purpose model score.

- [Sums and Differences of Finite Sets](https://gyarmatikati.web.elte.hu/publ/sumdiffv.pdf): Main research objective: Establish sharp relationships and constructive bounds for sizes of finite sumsets and difference sets. Task connection: The paper derives the construction exponent 1 + log(|U−U|/|U+U|)/log(2 max U + 1) from a finite nonnegative integer set U containing zero. This is the local construction objective used by SCiEL: Finite-set sum and difference ratio.

Primary research addresses the underlying problem directly; scientific importance does not rely on the agent/framework paper.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/alphaevolve_math_problems/sums_diffs_finite_sets` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/sums_diffs_finite_sets/evaluator.py (evaluate and helper validators at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/alphaevolve_math_problems/sums_diffs_finite_sets/initial_program.py (original baseline)
- repository: https://github.com/google-deepmind/alphaevolve_results/blob/4226acbf237ff9ad10ba7673a2af127a2d8a5971/mathematical_results.ipynb (B.6, Data cell81, solution_1: original2003element publishedconstruction usedasexplicitwarmstart)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- The upstream evaluator provides no independently trusted validity boolean; a finite returned score remains unverified.
- The bounded seed is a known published AlphaEvolve construction, not the original SCiEL simulated-annealing seed. Its score is not a newly discovered result; the source JAX search remains archived and was not reproduced.

Runtime routes: The default suite uses the unchanged original JAX simulated-annealing initial_program.py and requires numpy, jax and tqdm. Only the separately selected upstream adapter uses adapters/recovered/sciel_sums_diffs/seed.py, a known published AlphaEvolve warm start; that route is not a new discovery or a reproduction of the original search.
