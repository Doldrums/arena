# Ambient integer sets with small largest Sidon subset

**Source collection:** [Problem-bank constructions: arithmetic and extremal sets: source-based research tasks](../../papers/science-prize_b.md)\
**Task id:** `science-number-theory-sidon-obstruction`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Return exactly 12 distinct integers in [0,128]. Evaluator exhaustively computes the largest subset with all unordered pair sums unique INCLUDING diagonals. MINIMIZE that maximum subset size. The candidate chooses a hard AMBIENT set; the evaluator solves Sidon extraction exactly. This reverses the outer optimization compared with constructing a large Sidon set in a fixed interval.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> candidate. Return exactly 12 distinct integers in [0,128]. Evaluator exhaustively computes the largest subset with all unordered pair sums unique INCLUDING diagonals. MINIMIZE that maximum subset size.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Alexandre Bailleul and Robin Riblet (2026, On the largest Sidon subset in a finite subset of R^N) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [On the largest Sidon subset in a finite subset of R^N](https://arxiv.org/abs/2605.03181), Alexandre Bailleul and Robin Riblet (2026)

Parameters: `{"size": 12, "bound": 128}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound the largest Sidon subset guaranteed in every finite real or integer set.

Why it matters: Quantifies the amount of additive structure unavoidably extractable from arbitrary finite sets.

- [On the largest Sidon subset in a finite subset of R^N](https://arxiv.org/abs/2605.03181): Main research objective: Bound the largest Sidon subset guaranteed in every finite real or integer set. Task connection: Primary author abstract defines H(n) with exactly the min–max objective; here n=12 and ambient integer bound 128. The candidate chooses a hard AMBIENT set; the evaluator solves Sidon extraction exactly. This reverses the outer optimization compared with constructing a large Sidon set in a fixed interval.

A primary research paper directly studies the mathematical objective; local finite scope and restrictions are explicit. This does not certify novelty, importance of the baseline itself, or current open status.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The candidate chooses a hard AMBIENT set; the evaluator solves Sidon extraction exactly. This reverses the outer optimization compared with constructing a large Sidon set in a fixed interval.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2605.03181 (Alexandre Bailleul and Robin Riblet (2026), On the largest Sidon subset in a finite subset of R^N. The candidate chooses a hard AMBIENT set; the evaluator solves Sidon extraction exactly. This reverses the outer optimization compared with constructing a large Sidon set in a fixed interval. Primary author abstract inspected; no use of its construction algorithm or claim to reproduce its theorem.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000426 (JSP-000426; pinned Justin Sun Prize bank revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Discovery source only; mathematical authorship remains with the cited researchers. Independent paraphrase and implementation.)

## Limitations

- Independent finite adaptation, not a Lean proof, prize submission, full solution, optimality proof or claim of mathematical novelty.
- Published source supplies the mathematical question; all verifier and starter code was written locally, with no upstream implementation imported.
- Finite bounds and the public starter are development instances. An accepted candidate establishes only the reported local feasible value; no asymptotic inference follows.
- Candidate Python code is trusted; this runner is not a malicious-code sandbox.
- The candidate chooses a hard AMBIENT set; the evaluator solves Sidon extraction exactly. This reverses the outer optimization compared with constructing a large Sidon set in a fixed interval.
