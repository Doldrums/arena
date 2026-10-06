# Large integer sets with bounded pairwise least common multiples

**Source collection:** [Problem-bank constructions: arithmetic and extremal sets: source-based research tasks](../../papers/science-prize_b.md)\
**Task id:** `science-number-theory-bounded-lcm`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Return a nonempty subset of [1,512] with lcm(a,b)<=512 for every pair. Maximize cardinality. Finite instance of the extremal bounded-lcm problem. The simple seed does not import Chen's asymptotic construction.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> candidate. Return a nonempty subset of [1,512] with lcm(a,b)<=512 for every pair. Maximize cardinality.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Yong-Gao Chen (1998, Sequences with bounded l.c.m. of each pair of terms) studies the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Sequences with bounded l.c.m. of each pair of terms](https://matwbn.icm.edu.pl/ksiazki/aa/aa84/aa8416.pdf), Yong-Gao Chen (1998)

Parameters: `{"n": 512}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the maximum size and structure of integer sets with every pairwise lcm bounded by x.

Why it matters: Studies an explicit extremal arithmetic set problem and its asymptotic structure.

- [Sequences with bounded l.c.m. of each pair of terms](https://matwbn.icm.edu.pl/ksiazki/aa/aa84/aa8416.pdf): Main research objective: Determine the maximum size and structure of integer sets with every pairwise lcm bounded by x. Task connection: Introduction and theorem on p. 71 define A_x and establish its asymptotic size; this task is x=512. Primary first-page text inspected. Finite instance of the extremal bounded-lcm problem. The simple seed does not import Chen's asymptotic construction.

A primary research paper directly studies the mathematical objective; local finite scope and restrictions are explicit. This does not certify novelty, importance of the baseline itself, or current open status.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Finite instance of the extremal bounded-lcm problem. The simple seed does not import Chen's asymptotic construction.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://matwbn.icm.edu.pl/ksiazki/aa/aa84/aa8416.pdf (Yong-Gao Chen (1998), Sequences with bounded l.c.m. of each pair of terms. Introduction and theorem on p. 71 define A_x and establish its asymptotic size; this task is x=512. Primary first-page text inspected.)
- paper: https://mathweb.ucsd.edu/~ronspubs/80_11_number_theory.pdf (Paul Erdős and Ronald L. Graham (1980), Old and New Problems and Results in Combinatorial Number Theory. Printed p. 87. Finite instance of the extremal bounded-lcm problem. The simple seed does not import Chen's asymptotic construction. Primary full text downloaded and inspected; the scanned monograph was OCRed locally and equation-sensitive passages checked against page images. No contemporary open/solved status is inferred from this historical publication.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0301-0400.md#JSP-000360 (JSP-000360; pinned Justin Sun Prize bank revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Discovery source only; mathematical authorship remains with the cited researchers. Independent paraphrase and implementation.)

## Limitations

- Independent finite adaptation, not a Lean proof, prize submission, full solution, optimality proof or claim of mathematical novelty.
- Published source supplies the mathematical question; all verifier and starter code was written locally, with no upstream implementation imported.
- Finite bounds and the public starter are development instances. An accepted candidate establishes only the reported local feasible value; no asymptotic inference follows.
- Candidate Python code is trusted; this runner is not a malicious-code sandbox.
- Finite instance of the extremal bounded-lcm problem. The simple seed does not import Chen's asymptotic construction.
