# Most frequent element order in the symmetric group S16

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-most-frequent-permutation-order-16`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> an attainable permutation order k in S16. Maximize the exact number of permutations of that order. All integer partitions of 16 are enumerated and their cycle-type multiplicities 16! / product(i**m_i * m_i!) are summed by cycle-length lcm. S16 is a finite exact rediscovery specialization. Degree 16 keeps every count below 2**53 so the common floating score envelope represents integer counts exactly.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> an attainable permutation order k in S16. Maximize the exact number of permutations of that order. All integer partitions of 16 are enumerated and their cycle-type multiplicities 16! / product(i**m_i * m_i!) are summed by cycle-length lcm.

## State of the art

In S_16 the most common order is 12, shared by 2,428,557,331,200 permutations (OEIS A061125). Enumerating all 231 cycle types (scripts/check_state_of_the_art.py) confirms that no other order is more frequent. Beker described the maximizing orders asymptotically.

Reference value: proven optimum `2428557331200` (reviewed 2026-09-24).

- [OEIS A061125: Number of degree-n permutations of order exactly 12](https://oeis.org/A061125)
- [The most probable order of a random permutation](https://arxiv.org/abs/2510.11698), Adrian Beker (2025)

Parameters: `{"n": 16}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Identify which element order is most probable for a uniformly random permutation.

Why it matters: The modal-order objective is the principal problem investigated in Beker's paper.

- [The most probable order of a random permutation](https://arxiv.org/abs/2510.11698): Main research objective: Identify which element order is most probable for a uniformly random permutation. Task connection: S16 is a finite exact rediscovery specialization. Degree 16 keeps every count below 2**53 so the common floating score envelope represents integer counts exactly.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- S16 is a finite exact rediscovery specialization. Degree 16 keeps every count below 2**53 so the common floating score envelope represents integer counts exactly. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/2510.11698 (Adrian Beker, The most probable order of a random permutation (2025). Author abstract inspected. It studies the maximal order probability and proves an asymptotic description of its maximizing orders. S16 is a finite exact rediscovery specialization. Degree 16 keeps every count below 2**53 so the common floating score envelope represents integer counts exactly.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000966 (JSP-000966; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- Finite enumeration does not reproduce or prove the asymptotic result. The local order cap and degree differ from the original feasibility draft's S32 instance.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
