# Small prime primitive roots for twelve prime moduli

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-small-prime-primitive-roots`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> twelve Python prime integers, one for each modulus [101,103,107,109,113,127,131,137,139,149,151,157]. Each root is at most 100000, coprime to its modulus, and has multiplicative order p-1. Minimize the sum of these prime roots. Twelve small fixed moduli provide a finite construction/rediscovery instance; exact orders are verified without reproducing the shifted sieve.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> twelve Python prime integers, one for each modulus [101,103,107,109,113,127,131,137,139,149,151,157]. Each root is at most 100000, coprime to its modulus, and has multiplicative order p-1. Minimize the sum of these prime roots.

## State of the art

The least prime primitive roots of the twelve moduli are 2, 5, 2, 11, 3, 3, 2, 3, 2, 2, 7 and 5 (OEIS A002233), summing to 47.

Reference value: proven optimum `47` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #985](https://www.erdosproblems.com/985), status: open.

- [OEIS A002233: Least prime primitive root of the n-th prime](https://oeis.org/A002233)
- [The Least Prime Primitive Root and the Shifted Sieve](https://arxiv.org/abs/math/9807104), Greg Martin (1997)

Parameters: `{"moduli": [101, 103, 107, 109, 113, 127, 131, 137, 139, 149, 151, 157], "maximum": 100000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound the smallest prime generator of the multiplicative group modulo a prime.

Why it matters: Prime generator size is the explicit research objective of Martin's number-theory paper.

- [The Least Prime Primitive Root and the Shifted Sieve](https://arxiv.org/abs/math/9807104): Main research objective: Bound the smallest prime generator of the multiplicative group modulo a prime. Task connection: Twelve small fixed moduli provide a finite construction/rediscovery instance; exact orders are verified without reproducing the shifted sieve.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Twelve small fixed moduli provide a finite construction/rediscovery instance; exact orders are verified without reproducing the shifted sieve. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://arxiv.org/abs/math/9807104 (Greg Martin, The Least Prime Primitive Root and the Shifted Sieve (1997). Author abstract and journal metadata inspected. The paper bounds least prime primitive roots and explicitly distinguishes unconditional almost-all-modulus and conditional all-modulus results. Twelve small fixed moduli provide a finite construction/rediscovery instance; exact orders are verified without reproducing the shifted sieve.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000818 (JSP-000818; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- All moduli are public and small. Optimizing their roots does not prove a uniform bound or justify the generalized Riemann hypothesis.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
