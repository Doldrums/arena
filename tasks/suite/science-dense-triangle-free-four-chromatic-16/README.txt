# Dense triangle-free graphs on 16 vertices with chromatic number at least four

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-dense-triangle-free-four-chromatic-16`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of edges [u, v] of a simple triangle-free graph on vertices 0..15 that is not 3-colourable (exact backtracking). Maximize the number of edges. A valid graph with m edges shows f_4(16) > m; the published formula applies only to n >= 150.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of edges [u, v] of a simple triangle-free graph on vertices 0..15 that is not 3-colourable (exact backtracking). Maximize the number of edges.

## State of the art

No documented value for n = 16; for n >= 150 the maximum is floor((n-3)^2/4) + 5 edges (Ren, Wang, Wang and Yang 2024).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1011](https://www.erdosproblems.com/1011), status: open.

- [Extremal triangle-free graphs with chromatic number at least four](https://arxiv.org/abs/2404.07486), Sijie Ren, Jian Wang, Shipeng Wang, Weihua Yang (2024)

Parameters: `{"n": 16}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the maximum number of edges of triangle-free graphs with chromatic number at least r.

Why it matters: Erdős Problem #1011 asks for f_r(n); small orders show where the large-n extremal structure takes over.

- [Extremal triangle-free graphs with chromatic number at least four](https://arxiv.org/abs/2404.07486): Main research objective: Determine the maximum number of edges of triangle-free graphs with chromatic number at least r. Task connection: A valid graph with m edges shows f_4(16) > m; the published formula applies only to n >= 150.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- A valid graph with m edges shows f_4(16) > m; the published formula applies only to n >= 150. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2404.07486 (Sijie Ren, Jian Wang, Shipeng Wang and Weihua Yang, Extremal triangle-free graphs with chromatic number at least four (2024). arXiv record inspected; Erdős Problem #1011 page inspected: f_4(n) = floor((n-3)^2/4) + 6 for n >= 150 (Ren, Wang, Wang and Yang), where f_4(n) edges force a triangle in 4-chromatic graphs. A valid graph with m edges shows f_4(16) > m; the published formula applies only to n >= 150.)
- archive: https://www.erdosproblems.com/1011 (Erdős Problem #1011 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000841 (JSP-000841; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for n = 16 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
