# 3-colouring five fixed cycle-plus-triangles graphs

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-cycle-plus-triangles-colouring`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> five colourings (one colour in {0, 1, 2} per vertex), one per instance from cycle_plus_triangles(n, seed) for n = 30, 60, 90, 150, 300 with seeds 401..405 in the verifier: the Hamiltonian cycle 0-1-...-(n-1)-0 plus a random partition into triangles avoiding cycle edges. The score is the number of properly coloured instances (0..5). Maximize; every instance is 3-colourable by the Fleischner-Stiebitz theorem. The score counts fixed instances coloured properly; it measures a constructive colouring method for graphs whose colourability is known only through an algebraic proof.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> five colourings (one colour in {0, 1, 2} per vertex), one per instance from cycle_plus_triangles(n, seed) for n = 30, 60, 90, 150, 300 with seeds 401..405 in the verifier: the Hamiltonian cycle 0-1-...-(n-1)-0 plus a random partition into triangles avoiding cycle edges. The score is the number of properly coloured instances (0..5). Maximize; every instance is 3-colourable by the Fleischner-Stiebitz theorem.

## State of the art

Instance-solving task; every instance is 3-colourable, so 5 is attainable.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #842](https://www.erdosproblems.com/842), status: proved (Fleischner and Stiebitz).

- [A solution to a colouring problem of P. Erdős](https://doi.org/10.1016/0012-365X(92)90588-7), Herbert Fleischner, Michael Stiebitz (1992)
- [Erdős Problem #842](https://www.erdosproblems.com/842)

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Show that every cycle-plus-triangles graph is 3-colourable (Erdős Problem #842; proved non-constructively).

Why it matters: The Fleischner-Stiebitz proof is non-constructive, so efficient colouring procedures are of independent interest.

- [A solution to a colouring problem of P. Erdős](https://doi.org/10.1016/0012-365X(92)90588-7): Main research objective: Show that every cycle-plus-triangles graph is 3-colourable (Erdős Problem #842; proved non-constructively). Task connection: The score counts fixed instances coloured properly; it measures a constructive colouring method for graphs whose colourability is known only through an algebraic proof.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The score counts fixed instances coloured properly; it measures a constructive colouring method for graphs whose colourability is known only through an algebraic proof. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/0012-365X(92)90588-7 (Herbert Fleischner and Michael Stiebitz, A solution to a colouring problem of P. Erdős (1992). Crossref record inspected; Erdős Problem #842 page inspected (the cycle-plus-triangles problem, proved by Fleischner and Stiebitz via the Alon-Tarsi method). The score counts fixed instances coloured properly; it measures a constructive colouring method for graphs whose colourability is known only through an algebraic proof.)
- archive: https://www.erdosproblems.com/842 (Erdős Problem #842 (proved (Fleischner and Stiebitz)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000698 (JSP-000698; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Instance-solving task on five fixed pseudo-random instances.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
