# Graphs of girth at least five on 45 vertices with many edges

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-girth-five-extremal-45`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of a simple graph on vertices 0..44 with no triangle and no four-cycle. Maximize the number of edges; the known optimum is 145. The exact value 145 for n = 45 is known; recovering it tests constructions of dense girth-5 graphs.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple graph on vertices 0..44 with no triangle and no four-cycle. Maximize the number of edges; the known optimum is 145.

## State of the art

ex(45;{C3,C4}) = 145 (Backelin 2015; Afzaly and McKay tables, unique extremal graph).

Reference value: proven optimum `145` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #573](https://www.erdosproblems.com/573), status: open.

- [Sizes of the extremal girth 5 graphs of orders from 40 to 49](https://arxiv.org/abs/1511.08128), Jörgen Backelin (2015)
- [Extremal Graphs and Turán numbers (data by Narjess Afzaly and Brendan McKay)](https://users.cecs.anu.edu.au/~bdm/data/extremal.html), Narjess Afzaly, Brendan D. McKay

Parameters: `{"n": 45, "lengths": [3, 4]}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the maximum number of edges in graphs of girth at least five.

Why it matters: Erdős and Simonovits asked whether ex(n;{C3,C4}) ~ (n/2)^(3/2) (Erdős Problem #573); exact values are the finite data for this question.

- [Sizes of the extremal girth 5 graphs of orders from 40 to 49](https://arxiv.org/abs/1511.08128): Main research objective: Determine the maximum number of edges in graphs of girth at least five. Task connection: The exact value 145 for n = 45 is known; recovering it tests constructions of dense girth-5 graphs.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The exact value 145 for n = 45 is known; recovering it tests constructions of dense girth-5 graphs. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/1511.08128 (Jörgen Backelin, Sizes of the extremal girth 5 graphs of orders from 40 to 49 (2015). arXiv record inspected; Afzaly-McKay extremal graph tables inspected: ex(45;{C3,C4}) = 145 with a unique extremal graph (exact values through n = 53). Erdős Problem #573 page inspected. The exact value 145 for n = 45 is known; recovering it tests constructions of dense girth-5 graphs.)
- archive: https://www.erdosproblems.com/573 (Erdős Problem #573 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000463 (JSP-000463; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case (value and extremal graph are published).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
