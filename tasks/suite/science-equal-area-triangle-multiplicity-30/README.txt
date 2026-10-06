# Many equal-area triangles from 30 planar points

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-equal-area-triangle-multiplicity-30`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> exactly 30 distinct integer coordinate pairs in [-30,30]^2. Compute the absolute determinant for every triple, exclude zero-area triples, and maximize the largest multiplicity of a single positive doubled area. The local bounded integer configurations give lower constructions for positive-area multiplicity; they do not reproduce the paper's asymptotic upper-bound proof.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly 30 distinct integer coordinate pairs in [-30,30]^2. Compute the absolute determinant for every triple, exclude zero-area triples, and maximize the largest multiplicity of a single positive doubled area.

## State of the art

No documented maximum for 30 points in [-30,30]^2. Asymptotically the maximum number of equal-area triangles is between n^2 log log n (Erdős and Purdy) and O(n^(20/9)) (Raz and Sharir), Erdős Problem #1086.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1086](https://www.erdosproblems.com/1086), status: open.

- [Extremal problems on triangle areas in two and three dimensions](https://doi.org/10.1016/j.jcta.2009.03.008), Adrian Dumitrescu, Micha Sharir, Csaba D. Tóth (2009)

Parameters: `{"n": 30, "bound": 30}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound how often a fixed positive triangle area can occur in a finite point set.

Why it matters: The score counts the geometric incidence phenomenon that is a main research objective of the cited paper.

- [Extremal problems on triangle areas in two and three dimensions](https://arxiv.org/abs/0710.4109): Main research objective: Bound how often a fixed positive triangle area can occur in a finite point set. Task connection: The local bounded integer configurations give lower constructions for positive-area multiplicity; they do not reproduce the paper's asymptotic upper-bound proof.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The local bounded integer configurations give lower constructions for positive-area multiplicity; they do not reproduce the paper's asymptotic upper-bound proof. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/0710.4109 (Adrian Dumitrescu, Micha Sharir, and Csaba D. Tóth, Extremal problems on triangle areas in two and three dimensions (2007). Author abstract inspected. The paper directly bounds the number of equal-area triangles determined by finite point sets. The local bounded integer configurations give lower constructions for positive-area multiplicity; they do not reproduce the paper's asymptotic upper-bound proof.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000903 (JSP-000903; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- Integer coordinates are a strict restriction of arbitrary real planar configurations. Collinear triples never contribute, and a finite score is not a general extremal theorem.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
