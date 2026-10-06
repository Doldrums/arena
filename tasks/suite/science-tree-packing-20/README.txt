# Packing trees T1..T20 into K20 (Gyárfás tree packing conjecture)

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-tree-packing-20`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 20 entries; entry k-1 is None or an injective list of host vertices in 0..19 for the fixed tree T_k on k vertices (Prüfer-sequence trees from instance_trees(20, 611) in the verifier). Embedded trees must be edge-disjoint in K20. Maximize the number of packed edges; a complete packing uses all 190 edges. The conjecture predicts a perfect packing (190 edges) for this fixed tree sequence; scores measure packing search on one instance.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 20 entries; entry k-1 is None or an injective list of host vertices in 0..19 for the fixed tree T_k on k vertices (Prüfer-sequence trees from instance_trees(20, 611) in the verifier). Embedded trees must be edge-disjoint in K20. Maximize the number of packed edges; a complete packing uses all 190 edges.

## State of the art

No published packing for this generated sequence; the conjecture predicts a complete packing of all 190 edges.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Packing the largest trees in the tree packing conjecture](https://doi.org/10.4171/jems/1794), Barnabás Janzer, Richard Montgomery (2026)

Parameters: `{"n": 20, "seed": 611}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Prove the Gyárfás tree packing conjecture.

Why it matters: The tree packing conjecture (Gyárfás, 1976) is a central open problem on graph packings with recent asymptotic progress.

- [Packing the largest trees in the tree packing conjecture](https://doi.org/10.4171/jems/1794): Main research objective: Prove the Gyárfás tree packing conjecture. Task connection: The conjecture predicts a perfect packing (190 edges) for this fixed tree sequence; scores measure packing search on one instance.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The conjecture predicts a perfect packing (190 edges) for this fixed tree sequence; scores measure packing search on one instance. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4171/jems/1794 (Barnabás Janzer and Richard Montgomery, Packing the largest trees in the tree packing conjecture (2026). Crossref record inspected. The Gyárfás tree packing conjecture states that any trees T_1..T_n with |T_i| = i pack edge-disjointly into K_n; Janzer and Montgomery pack the largest trees under degree conditions. The conjecture predicts a perfect packing (190 edges) for this fixed tree sequence; scores measure packing search on one instance.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000611 (JSP-000611; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Instance-solving task on one fixed pseudo-random tree sequence; a full packing would be consistent with, not a proof of, the conjecture.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
