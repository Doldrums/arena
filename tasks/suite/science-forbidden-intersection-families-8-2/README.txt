# Families of subsets of an 8-set with no two members meeting in exactly 2 elements

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-forbidden-intersection-families-8-2`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct subsets of {1, ..., 8} (lists of elements) such that no two distinct members intersect in exactly 2 elements. Maximize the number of subsets; the optimum is T(8,2) = 67. For n = 8 and r = 2 the optimum is 67, so the task recovers an extremal family.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct subsets of {1, ..., 8} (lists of elements) such that no two distinct members intersect in exactly 2 elements. Maximize the number of subsets; the optimum is T(8,2) = 67.

## State of the art

T(8,2) = 67 (OEIS A390645), attained by the Frankl-Füredi construction.

Reference value: proven optimum `67` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #703](https://www.erdosproblems.com/703), status: proved ($250; Frankl and Rödl).

- [OEIS A390645](https://oeis.org/A390645)
- [On hypergraphs without two edges intersecting in a given number of vertices](https://doi.org/10.1016/0097-3165(84)90008-6), P. Frankl, Z. Füredi (1984)
- [Forbidden intersections](https://doi.org/10.1090/S0002-9947-1987-0871675-6), Peter Frankl, Vojtěch Rödl (1987)

Parameters: `{"n": 8, "r": 2}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate T(n,r), the largest family of subsets of an n-set with no two members meeting in exactly r elements (Erdős Problem #703).

Why it matters: Forbidden-intersection theorems (Frankl-Wilson, Frankl-Rödl) drive bounds for the chromatic number of Euclidean space and for coding theory.

- [On hypergraphs without two edges intersecting in a given number of vertices](https://doi.org/10.1016/0097-3165(84)90008-6): Main research objective: Estimate T(n,r), the largest family of subsets of an n-set with no two members meeting in exactly r elements (Erdős Problem #703). Task connection: For n = 8 and r = 2 the optimum is 67, so the task recovers an extremal family.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 8 and r = 2 the optimum is 67, so the task recovers an extremal family. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/0097-3165(84)90008-6 (Péter Frankl and Zoltán Füredi, On hypergraphs without two edges intersecting in a given number of vertices (1984). Crossref records inspected (Frankl and Füredi 1984; Frankl and Rödl 1987). Erdős Problem #703 page inspected ($250; Frankl and Rödl proved T(n,r) < (2-delta)^n for eps*n < r < (1/2-eps)n; Frankl and Füredi determined the extremal families for large n). OEIS A390645 inspected: T(8,2) = 67, attained by the Frankl-Füredi family {A : |A \ {1}| >= 5} together with all sets of size at most 1. For n = 8 and r = 2 the optimum is 67, so the task recovers an extremal family.)
- archive: https://www.erdosproblems.com/703 (Erdős Problem #703 (proved ($250; Frankl and Rödl)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000573 (JSP-000573; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
