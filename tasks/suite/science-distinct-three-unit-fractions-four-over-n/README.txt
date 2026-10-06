# Distinct three-term unit-fraction representations of 4/n

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-distinct-three-unit-fractions-four-over-n`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 254 rows for n=3..256. Each row is None or three DISTINCT positive integer denominators x,y,z<=1000000000000 with 1/x+1/y+1/z=4/n. Maximize fraction solved. Equality is checked by cross multiplication and malformed claims invalidate the candidate. Construct distinct positive denominators for n=3..256, with denominator bound10^12. The prize bank requires distinctness, which is stricter than the paper’s general solution definition; no universal proof or published computation is reproduced.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 254 rows for n=3..256. Each row is None or three DISTINCT positive integer denominators x,y,z<=1000000000000 with 1/x+1/y+1/z=4/n. Maximize fraction solved. Equality is checked by cross multiplication and malformed claims invalidate the candidate.

## State of the art

For every n from 3 to 256, 4/n is a sum of three distinct unit fractions with denominators far below 10^12 (found for every n by scripts/check_state_of_the_art.py), so the maximum fraction is 1. The general statement is Erdős Problem #242.

Reference value: proven optimum `1.0` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #242](https://www.erdosproblems.com/242), status: open (falsifiable).

- [Counting the number of solutions to the Erdős-Straus equation on unit fractions](https://arxiv.org/abs/1107.1010), Christian Elsholtz, Terence Tao (2013)

Parameters: `{"start": 3, "count": 254, "maximum": 1000000000000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand existence and multiplicity of three-term unit-fraction decompositions of 4/n.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Counting the number of solutions to the Erdos-Straus equation on unit fractions](https://arxiv.org/abs/1107.1010): Main research objective: Understand existence and multiplicity of three-term unit-fraction decompositions of 4/n. Task connection: Construct distinct positive denominators for n=3..256, with denominator bound10^12. The prize bank requires distinctness, which is stricter than the paper’s general solution definition; no universal proof or published computation is reproduced.

A problem-focused primary paper studies the same substantive mathematical construction or extremal quantity. No novelty claim is implied.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Independent finite certificate evaluator and local seed; no source implementation copied. Exact constraints are verified, but no optimality, general theorem, Lean proof, published record, or prize eligibility is claimed. See task sources and adaptation limitations.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/1107.1010 (Christian Elsholtz and Terence Tao, Counting the number of solutions to the Erdos-Straus equation on unit fractions. Author abstract inspected: positive-integer solutions to 4/n=1/x+1/y+1/z and bounds on their counts. Published in Journal of the Australian Mathematical Society 94 (2013), 50–105.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0201-0300.md#JSP-000213 (JSP-000213; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Construct distinct positive denominators for n=3..256, with denominator bound10^12. The prize bank requires distinctness, which is stricter than the paper’s general solution definition; no universal proof or published computation is reproduced.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
