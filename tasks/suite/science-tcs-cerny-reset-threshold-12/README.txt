# Černý problem: 12-state binary automata with long reset thresholds

**Source collection:** [Prize-listed mathematical problems: source-based research tasks](../../papers/science-prize.md)\
**Task id:** `science-tcs-cerny-reset-threshold-12`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

Construct a complete deterministic automaton with 12 states and two input letters that synchronizes, maximizing the length of its shortest reset word. Breadth-first search on the subset automaton computes the exact threshold and returns a shortest word. This is a finite construction adaptation of JSP-000022; a finite high score cannot prove the universal Černý conjecture.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> two length-N lists of destination states in 0..N-1, defining a complete binary deterministic automaton. It must synchronize. Score is its EXACT shortest reset-word length, maximized. The evaluator exhaustively searches the subset automaton and reports a shortest word. Fixed N=12 is a local finite restriction, not a proof of Černý's general conjecture.

Parameters: `{"n": 12}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine extremal shortest reset-word lengths of synchronizing finite automata.

Why it matters: The paper studies finite automata and reset thresholds as its mathematical research objective.

- [The Černý conjecture for small automata: experimental report](https://arxiv.org/abs/1301.2092): Main research objective: Determine extremal shortest reset-word lengths of synchronizing finite automata. Task connection: The local task searches complete binary automata on12 states, whereas the cited paper reports exhaustive results up to11; local BFS verifies each candidate only.

Underlying mathematical problem is studied directly by the cited primary source; finite task scope and rediscovery are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent BFS implementation of the mathematical reset threshold, not copied from the cited algorithms. Tests recover (n-1)^2 on the classical Černý family and cross-check exhaustive word enumeration for small automata. A score above the conjectured bound is not rejected; it would require independent review.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/1301.2092 (Jakub Kowalski and Marek Szykuła, The Černý conjecture for small automata: experimental report (2013): complete binary automata, shortest reset thresholds, and finite exhaustive experiments. The local n=12 search is not a reproduction of their exhaustive n<=11 classification.)
- paper: https://doi.org/10.4230/LIPIcs.ESA.2022.85 (Marek Szykuła and Adam Zyzik, An Improved Algorithm for Finding the Shortest Synchronizing Words (ESA 2022). Reset-word definition and exact threshold objective; this local simple BFS is independently written and does not claim to implement their improved algorithm.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000022 (JSP-000022: general Černý conjecture; restriction to 12 states, binary alphabet, finite construction scoring is local.)

## Limitations

- These are independently implemented finite certificate/search tasks. They are not Lean proofs, prize submissions, full general-conjecture solutions, or claims of eligibility or mathematical novelty.
- The prize catalog is a discovery source whose statements and contributor records can change. The pinned revision is recorded; original mathematical authorship is separate from this local implementation.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
- No formal proof of the general conjecture, exhaustive enumeration of 12-state automata, or current best-known threshold is claimed. (n-1)^2 is a conjectured bound and is never used to reject a larger valid score.
- The simple seed has threshold 1. Tests use the classical Černý automaton with threshold 121 as a published mathematical construction, not copied implementation.
- Distinct from searching a short reset word for a given automaton: the candidate here designs the automaton, and the verifier independently determines the minimum word length.
