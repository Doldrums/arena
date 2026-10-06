# Small tournaments in which every four vertices have a common dominator (Schütte's problem, k = 4)

**Source collection:** [Problem-bank constructions: Ramsey theory and colourings: source-based research tasks](../../papers/science-prize_e.md)\
**Task id:** `science-tournament-four-dominated`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> {'n': n, 'orientation': [...]}: one bit per pair (i,j), i<j, of vertices 0..n-1 in lexicographic order (0 means i -> j, 1 means j -> i), 5 <= n <= 90. Every set of 4 vertices must have a vertex with arcs to all four. Minimize n. A valid tournament on n vertices certifies f(4) <= n. The smallest known has 67 vertices; Erdős's lower bound gives f(4) >= 31.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'orientation': [...]}: one bit per pair (i,j), i<j, of vertices 0..n-1 in lexicographic order (0 means i -> j, 1 means j -> i), 5 <= n <= 90. Every set of 4 vertices must have a vertex with arcs to all four. Minimize n.

## State of the art

Smallest known tournament with every 4 vertices dominated: the Paley tournament on 67 vertices (OEIS A362137); f(4) >= 31 from Erdős's bound 2^(k+1)-1.

Reference value: best known value `67` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #902](https://www.erdosproblems.com/902), status: open.

- [OEIS A362137: smallest n-paradoxical tournament built as a directed Paley graph](https://oeis.org/A362137)
- [A Constructive Solution to a Tournament Problem](https://doi.org/10.4153/CMB-1971-007-1), R. L. Graham, J. H. Spencer (1971)

Parameters: `{"k": 4, "max_vertices": 90}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the smallest tournament in which every k vertices are dominated by another vertex.

Why it matters: Schütte's problem (Erdős Problem #902) is a classical tournament question connected to Paley constructions and probabilistic lower bounds; only k <= 3 is solved.

- [On a Problem of Schütte and Erdös](https://doi.org/10.2307/3612854): Main research objective: Determine the smallest tournament in which every k vertices are dominated by another vertex. Task connection: A valid tournament on n vertices certifies f(4) <= n. The smallest known has 67 vertices; Erdős's lower bound gives f(4) >= 31.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid tournament on n vertices certifies f(4) <= n. The smallest known has 67 vertices; Erdős's lower bound gives f(4) >= 31. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.2307/3612854 (Esther Szekeres and George Szekeres, On a Problem of Schütte and Erdös (1965). Crossref record inspected (JSTOR full text not accessible); Erdős Problem #902 page inspected: f(1)=3, f(2)=7, Szekeres and Szekeres proved f(3)=19, and 2^(k+1)-1 <= f(k). OEIS A362137 inspected: the smallest known 4-paradoxical tournament is the Paley tournament on 67 vertices. A valid tournament on n vertices certifies f(4) <= n. The smallest known has 67 vertices; Erdős's lower bound gives f(4) >= 31.)
- archive: https://www.erdosproblems.com/902 (Erdős Problem #902 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000750 (JSP-000750; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- The Paley(83) starter is larger than the known Paley(67) construction; local checks confirm Paley tournaments of order 19, 43, 47 and 59 fail and 67, 71, 79, 83 pass.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
