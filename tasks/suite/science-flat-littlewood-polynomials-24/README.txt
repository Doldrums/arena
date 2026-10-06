# Flattest plus-minus-one polynomials with 24 coefficients (minimum sup norm)

**Source collection:** [Problem-bank constructions: discrete geometry and analysis: source-based research tasks](../../papers/science-prize_g.md)\
**Task id:** `science-flat-littlewood-polynomials-24`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> 24 coefficients in {+1, -1} of P(z) = sum c_k z^k. The score is max over |z| = 1 of |P(z)| divided by sqrt(24), computed by dense sampling and golden-section refinement of the highest peaks (accuracy about 1e-9). Minimize; the exhaustive optimum is 1.2583758. The exact minimum for 24 coefficients (degree 23) is recovered; Odlyzko's online tables list the optimal polynomials.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 24 coefficients in {+1, -1} of P(z) = sum c_k z^k. The score is max over |z| = 1 of |P(z)| divided by sqrt(24), computed by dense sampling and golden-section refinement of the highest peaks (accuracy about 1e-9). Minimize; the exhaustive optimum is 1.2583758.

## State of the art

Exhaustive search (Odlyzko 2018 for all degrees <= 52; recomputed here with a certified grid bound) gives min max|P|/sqrt(24) = 1.2583758 for 24 coefficients.

Reference value: proven optimum `1.2583758` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1150](https://www.erdosproblems.com/1150), status: open.

- [Search for Ultraflat Polynomials with Plus and Minus One Coefficients](https://doi.org/10.1017/9781316650295.004), Andrew Odlyzko (2018)

Parameters: `{"n": 24}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how flat polynomials with plus-minus-one coefficients can be on the unit circle.

Why it matters: Littlewood's flatness problem and Erdős's conjecture max|P| > (1+c)sqrt(n) (Erdős Problem #1150) are classical open problems in analysis with engineering applications.

- [Search for Ultraflat Polynomials with Plus and Minus One Coefficients](https://doi.org/10.1017/9781316650295.004): Main research objective: Determine how flat polynomials with plus-minus-one coefficients can be on the unit circle. Task connection: The exact minimum for 24 coefficients (degree 23) is recovered; Odlyzko's online tables list the optimal polynomials.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The exact minimum for 24 coefficients (degree 23) is recovered; Odlyzko's online tables list the optimal polynomials. Exact local certificates are not Lean proofs; floating-point scores are stated as such. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1017/9781316650295.004 (Andrew Odlyzko, Search for Ultraflat Polynomials with Plus and Minus One Coefficients (2018). Author's paper (revised 2017) inspected: exhaustive searches over all +-1 polynomials of degree n <= 52 determine M_n = min max|F|/sqrt(n+1), with M_n appearing to converge to about 1.27. Erdős Problem #1150 page inspected. The value for 24 coefficients was recomputed locally by a certified exhaustive search (grid bound grid <= max <= grid/cos(pi*23/1024)). The exact minimum for 24 coefficients (degree 23) is recovered; Odlyzko's online tables list the optimal polynomials.)
- archive: https://www.erdosproblems.com/1150 (Erdős Problem #1150 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000955 (JSP-000955; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case by exhaustive search. The reference value 1.2583758 was recomputed locally because Odlyzko's online tables were not retrievable during review.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
