# Consecutive powerful non-squares: exact counterexample certificate

**Source collection:** [Prize-listed mathematical problems: source-based research tasks](../../papers/science-prize.md)\
**Task id:** `science-number-theory-powerful-consecutive-counterexample`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Provide a positive integer n and complete prime factorizations certifying that n and n+1 are powerful and neither is a square. Every prime exponent must be at least two. The verifier uses exact integers and primality tests. This recreates the resolved yes/no question in JSP-000301, with a local certificate-size bound n+1 <= 10^12 and binary validity score. The published 12167/12168 witness is explicitly credited to Solomon W. Golomb.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'n': int, 'factorizations': [factors_of_n, factors_of_n_plus_1]}; each factorization is a list of distinct [prime, exponent] pairs. Require 2 <= n < 10**12, every exponent >= 2, complete prime factorizations, and neither integer a square. Score 1 for a valid disproof witness; otherwise invalid. This is a solved-problem rediscovery task, not an optimization leaderboard or Lean proof.

Parameters: `{"maximum": 1000000000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct and understand consecutive powerful integers neither of which is a square.

Why it matters: The primary paper studies the structure and Diophantine construction of Type II powerful-number pairs.

- [Consecutive integer pairs of powerful numbers and related Diophantine equations](https://www.fq.math.ca/Scanned/14-2/walker.pdf): Main research objective: Construct and understand consecutive powerful integers neither of which is a square. Task connection: The local certificate is one already known Type II pair, checked exactly; it does not reproduce the general parametrization or count all pairs.

Underlying mathematical problem is studied directly by the cited primary source; finite task scope and rediscovery are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- JSP-000301 is the existence/disproof question, not Erdős #365's separate counting question. The published Golomb witness is a baseline, not a new discovery. Exact arithmetic does not establish Lean verification or award eligibility.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1080/00029890.1970.11992598 (Solomon W. Golomb, Powerful Numbers, American Mathematical Monthly 77(8), 1970, pp.848–852. Publisher metadata establishes author/title; the prize record explicitly attributes the 12167 counterexample to this paper. Full paper text was not independently accessible during this review.)
- paper: https://www.fq.math.ca/Scanned/14-2/walker.pdf (David T. Walker, Consecutive integer pairs of powerful numbers and related Diophantine equations, Fibonacci Quarterly 14(2), 1976, pp.111–116. Primary full text inspected: Type II pairs are consecutive powerful non-squares; mathematical witness discovery remains credited to Golomb, not to this local implementation.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0301-0400.md#JSP-000301 (JSP-000301: scoped yes/no question and explicit Golomb counterexample attribution; source revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased specification; no implementation copied.)

## Limitations

- These are independently implemented finite certificate/search tasks. They are not Lean proofs, prize submissions, full general-conjecture solutions, or claims of eligibility or mathematical novelty.
- The prize catalog is a discovery source whose statements and contributor records can change. The pinned revision is recorded; original mathematical authorship is separate from this local implementation.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
- The bound restricts representable certificates but does not weaken an accepted counterexample: a single verified pair disproves the universal claim. This does not solve the distinct, open counting question in Erdős problem #365.
- The baseline embeds the already published mathematical witness and scores 1. This is a verification/rediscovery task; there is no claim of optimization headroom, least-counterexample proof, or new result.
