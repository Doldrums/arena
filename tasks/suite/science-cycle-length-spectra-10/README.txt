# Realizing every set of cycle lengths on 10 vertices

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-cycle-length-spectra-10`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a list of at most 500 simple graphs on vertices 0..9, each a list of edges [u, v]. The cycle set of a graph (the lengths of its cycles, computed exactly by dynamic programming over paths) is recorded for every graph. Maximize the number of distinct cycle sets; the optimum is 133. There are exactly 133 cycle sets on 10 vertices, so a complete collection recovers f(10).

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a list of at most 500 simple graphs on vertices 0..9, each a list of edges [u, v]. The cycle set of a graph (the lengths of its cycles, computed exactly by dynamic programming over paths) is recorded for every graph. Maximize the number of distinct cycle sets; the optimum is 133.

## State of the art

f(10) = 133 (OEIS A399654).

Reference value: proven optimum `133` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #84](https://www.erdosproblems.com/84), status: open.

- [OEIS A399654](https://oeis.org/A399654)
- [Improved bound on the number of cycle sets](https://doi.org/10.5070/C66165704), Rajko Nenadov (2026)
- [Unavoidable cycle lengths in graphs](https://doi.org/10.1002/jgt.20072), Jacques Verstraete (2005)

Parameters: `{"n": 10, "max_graphs": 500}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Count the possible cycle sets f(n) of graphs on n vertices (Erdős Problem #84).

Why it matters: Cycle spectra connect extremal graph theory with pancyclicity; the growth of f(n) between 2^(n/2) and 2^n is open.

- [Improved bound on the number of cycle sets](https://doi.org/10.5070/C66165704): Main research objective: Count the possible cycle sets f(n) of graphs on n vertices (Erdős Problem #84). Task connection: There are exactly 133 cycle sets on 10 vertices, so a complete collection recovers f(10).

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- There are exactly 133 cycle sets on 10 vertices, so a complete collection recovers f(10). Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.5070/C66165704 (Rajko Nenadov, Improved bound on the number of cycle sets (2026). Crossref record inspected; Erdős Problem #84 page inspected (Erdős and Faudree showed 2^(n/2) < f(n) <= 2^(n-2); Verstraëte proved f(n) = o(2^n); Nenadov improved the bound). OEIS A399654 inspected (Dunås 2026): f(10) = 133. There are exactly 133 cycle sets on 10 vertices, so a complete collection recovers f(10).)
- archive: https://www.erdosproblems.com/84 (Erdős Problem #84 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000100 (JSP-000100; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
