# Projective blocking sets with small line intersections in PG(2,7)

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-projective-blocking-intersections-pg27`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> distinct point indices in 0..56 for PG(2,7). Point order is (1,x,y) lexicographically for x,y=0..6, then (0,1,x), then (0,0,1). Every projective line must meet the set. Minimize the maximum intersection with any line; line-contained sets are allowed but score at least 8. The local task searches all point subsets in the prime plane of order seven; it does not constrain candidates to unions of algebraic curves or reproduce that paper's proof. The optimum is 4: an exhaustive search shows that no blocking set meets every line in at most 3 points, so this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct point indices in 0..56 for PG(2,7). Point order is (1,x,y) lexicographically for x,y=0..6, then (0,1,x), then (0,0,1). Every projective line must meet the set. Minimize the maximum intersection with any line; line-contained sets are allowed but score at least 8.

## State of the art

No blocking set of PG(2,7) meets every line in at most 3 points, while one meeting every line in at most 4 points exists. An exhaustive branch-and-bound search (scripts/check_state_of_the_art.py) establishes both, so the optimum is 4. The uniform question over all projective planes is Erdős Problem #1159.

Reference value: proven optimum `4` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1159](https://www.erdosproblems.com/1159), status: open.

- [Blocking sets from a union of plane curves](https://arxiv.org/abs/2510.15332), Shamil Asgarli, Dragos Ghioca, Chi Hoi Yip (2025)

Parameters: `{"q": 7}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct projective-plane blocking sets whose intersections with all lines are small.

Why it matters: Every verified improvement gives a finite construction for the same blocking-set intersection objective motivating the paper.

- [Blocking sets from a union of plane curves](https://arxiv.org/abs/2510.15332): Main research objective: Construct projective-plane blocking sets whose intersections with all lines are small. Task connection: The local task searches all point subsets in the prime plane of order seven; it does not constrain candidates to unions of algebraic curves or reproduce that paper's proof.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The local task searches all point subsets in the prime plane of order seven; it does not constrain candidates to unions of algebraic curves or reproduce that paper's proof. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2510.15332 (Shamil Asgarli, Dragos Ghioca, and Chi Hoi Yip, Blocking sets from a union of plane curves (2025). Author abstract inspected. It explicitly motivates constructions by Erdős' question on blocking sets meeting every line only a few times. The local task searches all point subsets in the prime plane of order seven; it does not constrain candidates to unions of algebraic curves or reproduce that paper's proof.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000964 (JSP-000964; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- Solved finite case: No blocking set of PG(2,7) meets every line in at most 3 points, while one meeting every line in at most 4 points exists.
- A result in this one Desarguesian plane says nothing about a uniform constant across arbitrary finite planes. The seed is a full line and is explicitly a trivial blocking set.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
