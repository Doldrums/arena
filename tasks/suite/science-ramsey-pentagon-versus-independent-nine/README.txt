# Pentagon-free graphs without independent 9-sets (Ramsey number R(C5,K9))

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-ramsey-pentagon-versus-independent-nine`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 35 containing no 5-cycle (as a subgraph) and no independent set of 9 vertices, both checked exactly. Maximize n. A valid graph on n vertices certifies R(C5,K9) > n; the best known has 32 vertices and no valid graph has more than 35.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': n, 'edges': [[u, v], ...]}: a simple graph on vertices 0..n-1 with 1 <= n <= 35 containing no 5-cycle (as a subgraph) and no independent set of 9 vertices, both checked exactly. Maximize n.

## State of the art

33 <= R(C5,K9) <= 36 (survey DS1.18, Table Vb; upper bound Lidický-Pfender); the lower bound comes from 8 disjoint copies of K4.

Reference value: best known value `32` (reviewed 2026-09-24).

- [Small Ramsey Numbers (Dynamic Survey DS1, revision 18, 24 April 2026)](https://doi.org/10.37236/21), Stanisław P. Radziszowski (2026)
- [Semidefinite Programming and Ramsey Numbers](https://doi.org/10.1137/18M1169473), Bernard Lidický, Florian Pfender (2021)

Parameters: `{"cycle": 5, "independent": 9, "max_vertices": 35}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the cycle-complete Ramsey number R(C5,K9).

Why it matters: Cycle-versus-clique Ramsey numbers are a central family of Ramsey problems (Erdős, Faudree, Rousseau and Schelp); small open cases test flag-algebra bounds.

- [Semidefinite Programming and Ramsey Numbers](https://doi.org/10.1137/18M1169473): Main research objective: Determine the cycle-complete Ramsey number R(C5,K9). Task connection: A valid graph on n vertices certifies R(C5,K9) > n; the best known has 32 vertices and no valid graph has more than 35.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid graph on n vertices certifies R(C5,K9) > n; the best known has 32 vertices and no valid graph has more than 35. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1137/18M1169473 (Bernard Lidický and Florian Pfender, Semidefinite Programming and Ramsey Numbers (2021). Crossref record inspected; Radziszowski's survey DS1.18 (Table Vb) inspected: 33 <= R(C5,K9) <= 36 with the upper bound from Lidický and Pfender's flag-algebra computations; the lower bound is attained by eight disjoint copies of K4. The conjecture R(Cn,Km) = (n-1)(m-1)+1 covers only n >= m, so this case is open. A valid graph on n vertices certifies R(C5,K9) > n; the best known has 32 vertices and no valid graph has more than 35.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000442 (JSP-000442; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Exact exhaustive checks; the vertex cap 35 is the proven upper limit.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
