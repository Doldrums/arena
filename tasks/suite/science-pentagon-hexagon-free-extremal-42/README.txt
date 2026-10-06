# Graphs on 42 vertices without five- or six-cycles

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-pentagon-hexagon-free-extremal-42`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of a simple graph on vertices 0..41 containing neither a five-cycle nor a six-cycle. Maximize the number of edges; the known optimum is 104. The exact value 104 for n = 42 is known; the task recovers it.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple graph on vertices 0..41 containing neither a five-cycle nor a six-cycle. Maximize the number of edges; the known optimum is 104.

## State of the art

ex(42;{C5,C6}) = 104 (Afzaly and McKay tables; at least 6 extremal graphs).

Reference value: proven optimum `104` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #574](https://www.erdosproblems.com/574), status: disproved.

- [Extremal Graphs and Turán numbers (data by Narjess Afzaly and Brendan McKay)](https://users.cecs.anu.edu.au/~bdm/data/extremal.html), Narjess Afzaly, Brendan D. McKay

Parameters: `{"n": 42, "lengths": [5, 6]}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine extremal numbers for excluding consecutive odd and even cycles.

Why it matters: This family (Erdős Problem #574) tested an Erdős-Simonovits conjecture that was later disproved; exact values expose the finite structure.

- [Compactness results in extremal graph theory](https://doi.org/10.1007/bf02579234): Main research objective: Determine extremal numbers for excluding consecutive odd and even cycles. Task connection: The exact value 104 for n = 42 is known; the task recovers it.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The exact value 104 for n = 42 is known; the task recovers it. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/bf02579234 (Paul Erdős and Miklós Simonovits, Compactness results in extremal graph theory (1982). Crossref record inspected; Erdős Problem #574 page inspected (the Erdős-Simonovits formula for ex(n;{C_(2k-1),C_2k}) was disproved for k = 3 and 5). Afzaly-McKay tables inspected: ex(42;{C5,C6}) = 104 exactly. The exact value 104 for n = 42 is known; the task recovers it.)
- archive: https://www.erdosproblems.com/574 (Erdős Problem #574 (disproved); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000464 (JSP-000464; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case per the published tables.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
