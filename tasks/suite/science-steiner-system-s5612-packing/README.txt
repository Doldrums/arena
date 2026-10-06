# Packings of 6-sets on 12 points with no repeated 5-subset (the Witt design S(5,6,12))

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-steiner-system-s5612-packing`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of distinct 6-subsets of 0..11 such that no 5-subset lies in two blocks. Maximize the number of blocks; the optimum 132 is attained exactly by the Steiner system S(5,6,12). Each block covers six 5-subsets of the 792, so at most 132 blocks fit; 132 is attained only by the Witt design S(5,6,12).

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of distinct 6-subsets of 0..11 such that no 5-subset lies in two blocks. Maximize the number of blocks; the optimum 132 is attained exactly by the Steiner system S(5,6,12).

## State of the art

132 = C(12,5)/C(6,5) blocks, attained by the Steiner system S(5,6,12) (Witt 1938).

Reference value: proven optimum `132` (reviewed 2026-09-24).

- [Über Steinersche Systeme](https://doi.org/10.1007/bf02948948), Ernst Witt (1938)
- [The existence of designs](https://arxiv.org/abs/1401.3665), Peter Keevash (2014)

Parameters: `{"points": 12, "block": 6, "strength": 5}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Establish existence of designs (Steiner systems) for all admissible parameters.

Why it matters: Existence of designs was a 19th-century problem solved by Keevash; the Witt design is a classical sporadic object tied to the Mathieu group M12.

- [The existence of designs](https://arxiv.org/abs/1401.3665): Main research objective: Establish existence of designs (Steiner systems) for all admissible parameters. Task connection: Each block covers six 5-subsets of the 792, so at most 132 blocks fit; 132 is attained only by the Witt design S(5,6,12).

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Each block covers six 5-subsets of the 792, so at most 132 blocks fit; 132 is attained only by the Witt design S(5,6,12). Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/1401.3665 (Peter Keevash, The existence of designs (2014). arXiv record for Keevash's existence theorem inspected; Crossref record for Witt's 'Über Steinersche Systeme' (Abh. Math. Sem. Hamburg 12) inspected. S(5,6,12) exists and is unique up to isomorphism. Each block covers six 5-subsets of the 792, so at most 132 blocks fit; 132 is attained only by the Witt design S(5,6,12).)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000590 (JSP-000590; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; the design is classical and unique.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
