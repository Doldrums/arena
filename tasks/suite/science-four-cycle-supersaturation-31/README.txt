# Fewest four-cycles in graphs with 31 vertices and 91 edges

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-four-cycle-supersaturation-31`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> exactly 91 distinct edges [u, v] on vertices 0..30 (one more than ex(31;C4) = 90). The score is the exact number of four-cycles (subgraphs). Minimize. n = 31 = 5^2+5+1 is a polarity-graph order with odd q = 5, not covered by the He-Ma-Yang theorem; no minimum count is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly 91 distinct edges [u, v] on vertices 0..30 (one more than ex(31;C4) = 90). The score is the exact number of four-cycles (subgraphs). Minimize.

## State of the art

No documented minimum for n = 31, m = 91. Erdős and Simonovits conjectured >> n^(1/2) four-cycles; proved by He, Ma and Yang for n = q^2+q+1 with even q.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #60](https://www.erdosproblems.com/60), status: open.

- [Some extremal results on 4-cycles](https://doi.org/10.1016/j.jctb.2021.01.007), Jialin He, Jie Ma, Tianchi Yang (2021)
- [Erdős Problem #60](https://www.erdosproblems.com/60)

Parameters: `{"n": 31, "edges": 91}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how many four-cycles are forced just above the C4 Turán number.

Why it matters: C4 supersaturation just above the extremal number (Erdős Problem #60) is open; finite minima indicate the true dependence on n.

- [Some extremal results on 4-cycles](https://doi.org/10.1016/j.jctb.2021.01.007): Main research objective: Determine how many four-cycles are forced just above the C4 Turán number. Task connection: n = 31 = 5^2+5+1 is a polarity-graph order with odd q = 5, not covered by the He-Ma-Yang theorem; no minimum count is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- n = 31 = 5^2+5+1 is a polarity-graph order with odd q = 5, not covered by the He-Ma-Yang theorem; no minimum count is documented. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/j.jctb.2021.01.007 (Jialin He, Jie Ma and Tianchi Yang, Some extremal results on 4-cycles (2021). Crossref record inspected; Erdős Problem #60 page inspected: Erdős and Simonovits conjectured that more than ex(n;C4) edges force >> n^(1/2) four-cycles; He, Ma and Yang proved it for n = q^2+q+1 with q even. ex(31;C4) = 90 per the Afzaly-McKay tables. n = 31 = 5^2+5+1 is a polarity-graph order with odd q = 5, not covered by the He-Ma-Yang theorem; no minimum count is documented.)
- archive: https://www.erdosproblems.com/60 (Erdős Problem #60 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000079 (JSP-000079; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented minimum for n = 31 (reference label none). The lexicographic starter is far from optimal.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
