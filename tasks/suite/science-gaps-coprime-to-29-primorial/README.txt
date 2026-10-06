# Which small gaps occur between consecutive integers coprime to 29#

**Source collection:** [Problem-bank constructions: number theory and additive sets: source-based research tasks](../../papers/science-prize_h.md)\
**Task id:** `science-gaps-coprime-to-29-primorial`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> up to 200 certificates [x, g] with 1 <= x <= 29# = 6469693230 and 2 <= g <= 1000, where x and x + g are coprime to 29# and every integer strictly between them shares a prime factor with 29#. The score is the largest L such that each even gap 2, 4, ..., L is certified. Maximize; the optimum is 46 (the gap 48 does not occur). For 29# every even gap up to 46 occurs and 48 does not, so the optimum is 46.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> up to 200 certificates [x, g] with 1 <= x <= 29# = 6469693230 and 2 <= g <= 1000, where x and x + g are coprime to 29# and every integer strictly between them shares a prime factor with 29#. The score is the largest L such that each even gap 2, 4, ..., L is certified. Maximize; the optimum is 46 (the gap 48 does not occur).

## State of the art

Every even gap up to 46 occurs between consecutive integers coprime to 29# and 48 does not (OEIS A389839).

Reference value: proven optimum `46` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #854](https://www.erdosproblems.com/854), status: open.

- [OEIS A389839: Smallest even number that is not a difference of consecutive numbers coprime to prime(n)#](https://oeis.org/A389839)
- [On the difference of consecutive numbers prime to n](https://doi.org/10.4064/aa-8-3-343-347), C. Hooley (1963)

Parameters: `{"count": 10}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine which even gaps occur between consecutive integers coprime to a primorial (Erdős Problem #854).

Why it matters: The gap structure of reduced residues modulo primorials underlies sieve models of prime gaps and Jacobsthal's function.

- [On the difference of consecutive numbers prime to n](https://doi.org/10.4064/aa-8-3-343-347): Main research objective: Determine which even gaps occur between consecutive integers coprime to a primorial (Erdős Problem #854). Task connection: For 29# every even gap up to 46 occurs and 48 does not, so the optimum is 46.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For 29# every even gap up to 46 occurs and 48 does not, so the optimum is 46. Exact local certificates are not Lean proofs; the Mahler measure and reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4064/aa-8-3-343-347 (C. Hooley, On the difference of consecutive numbers prime to n (1963). Crossref record inspected (Hooley studies the distribution of differences between consecutive reduced residues). Erdős Problem #854 page inspected (Erdős first expected every even number up to the maximal gap to occur, then doubted it after computations of Lacampagne and Selfridge for 13#). OEIS A389839 inspected: the smallest even number that is not a gap between consecutive integers coprime to 29# is 48. For 29# every even gap up to 46 occurs and 48 does not, so the optimum is 46.)
- archive: https://www.erdosproblems.com/854 (Erdős Problem #854 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000707 (JSP-000707; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case from the OEIS table.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
