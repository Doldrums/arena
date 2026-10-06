# Large sets with Property P

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-property-p-divisibility-256`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a nonempty subset of [1,n=256]. For every a<b<=c in the set, a must NOT divide b+c. Repeated larger summands b=c are included. Maximize cardinality. Finite cardinality maximization in [1,256], including repeated larger summands. The cited work proves the extremal bound for sufficiently large n; this task claims neither novelty nor its applicability threshold at 256.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty subset of [1,n=256]. For every a<b<=c in the set, a must NOT divide b+c. Repeated larger summands b=c are included. Maximize cardinality.

## State of the art

The maximum is 86 = floor(256/3) + 1, attained by {171, ..., 256}. An exact integer programme (151,333 divisibility constraints, solved to optimality with HiGHS; scripts/check_state_of_the_art.py --slow) shows that no larger subset of [1,256] has the property. Bedert proved the bound floor(n/3) + 1 for all sufficiently large n, as conjectured by Erdős and Sárközy.

Reference value: proven optimum `86` (reviewed 2026-09-24).

- [On a problem of Erdős and Sárközy about sequences with no term dividing the sum of two larger terms](https://arxiv.org/abs/2301.07065), Benjamin Bedert (2023)
- [On Erdős and Sárközy's sequences with Property P](https://doi.org/10.1007/s00605-016-0995-9), Christian Elsholtz, Stefan Planitzer (2016)

Parameters: `{"n": 256}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine extremal sizes of integer sets whose smaller elements do not divide sums of two larger elements.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [On a problem of Erdős and Sárközy about sequences with no term dividing the sum of two larger terms](https://arxiv.org/abs/2301.07065): Main research objective: Determine extremal sizes of integer sets whose smaller elements do not divide sums of two larger elements. Task connection: Finite cardinality maximization in [1,256], including repeated larger summands. The cited work proves the extremal bound for sufficiently large n; this task claims neither novelty nor its applicability threshold at 256.

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

- paper: https://arxiv.org/abs/2301.07065 (Benjamin Bedert, On a problem of Erdős and Sárközy about sequences with no term dividing the sum of two larger terms. Author abstract inspected. Repetition convention j<=k additionally checked in Elsholtz and Planitzer, On Erdős and Sárközy’s sequences with Property P, DOI 10.1007/s00605-016-0995-9 (2016).)
- paper: https://link.springer.com/article/10.1007/s00605-016-0995-9 (Christian Elsholtz and Stefan Planitzer, On Erdős and Sárközy’s sequences with Property P (2016): primary statement confirms i<j<=k, including repeated larger terms.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000051 (JSP-000051; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Finite cardinality maximization in [1,256], including repeated larger summands. The cited work proves the extremal bound for sufficiently large n; this task claims neither novelty nor its applicability threshold at 256.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
