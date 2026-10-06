# K4-free graphs on 18 vertices with small triangle-free induced subgraphs (Erdős-Rogers)

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-erdos-rogers-k4-free-18`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> list of edges [u, v] of a simple K4-free graph on vertices 0..17. The score is the largest number of vertices inducing a triangle-free subgraph (exact branch and bound). Minimize. A K4-free graph whose triangle-free induced subgraphs have at most s vertices certifies f(18) <= s; no exact value for n = 18 is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple K4-free graph on vertices 0..17. The score is the largest number of vertices inducing a triangle-free subgraph (exact branch and bound). Minimize.

## State of the art

No documented value for n = 18; asymptotically f(n) = n^(1/2+o(1)).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #620](https://www.erdosproblems.com/620), status: open.

- [On the order of the classical Erdős-Rogers functions](https://doi.org/10.1112/blms.13214), Dhruv Mubayi, Jacques Verstraëte (2024)
- [Erdős Problem #620](https://www.erdosproblems.com/620)

Parameters: `{"n": 18}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the Erdős-Rogers function: the largest triangle-free induced subgraph guaranteed in K4-free graphs.

Why it matters: The Erdős-Rogers problem (Erdős Problem #620) is a basic Ramsey-type question whose order was settled only recently.

- [On the order of the classical Erdős-Rogers functions](https://doi.org/10.1112/blms.13214): Main research objective: Determine the Erdős-Rogers function: the largest triangle-free induced subgraph guaranteed in K4-free graphs. Task connection: A K4-free graph whose triangle-free induced subgraphs have at most s vertices certifies f(18) <= s; no exact value for n = 18 is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A K4-free graph whose triangle-free induced subgraphs have at most s vertices certifies f(18) <= s; no exact value for n = 18 is documented. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1112/blms.13214 (Dhruv Mubayi and Jacques Verstraëte, On the order of the classical Erdős-Rogers functions (2024). Crossref record inspected; Erdős Problem #620 page inspected: f(n) = n^(1/2+o(1)) with the current bounds n^(1/2)(log n)^(1/2)/loglog n << f(n) << n^(1/2) log n (upper bound by Mubayi and Verstraëte). A K4-free graph whose triangle-free induced subgraphs have at most s vertices certifies f(18) <= s; no exact value for n = 18 is documented.)
- archive: https://www.erdosproblems.com/620 (Erdős Problem #620 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000502 (JSP-000502; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for n = 18 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
