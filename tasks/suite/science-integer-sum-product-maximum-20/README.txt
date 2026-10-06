# Integer sum-product extremal sets

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-integer-sum-product-maximum-20`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> n=20 distinct positive integers <=maximum=10000. Compute A+A and A*A with equal summands/factors allowed. Minimize max(|A+A|,|A*A|). Exactly 20 distinct positive integers at most 10000, minimizing the maximum of sumset and product-set sizes. This uses integers rather than arbitrary reals, and includes diagonal pairs.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> n=20 distinct positive integers <=maximum=10000. Compute A+A and A*A with equal summands/factors allowed. Minimize max(|A+A|,|A*A|).

## State of the art

No documented minimum of max(|A+A|, |AA|) for 20-element integer sets. The Erdős-Szemerédi sum-product conjecture is Erdős Problem #52. Solymosi proved max(|A+A|, |AA|) >= |A|^(4/3)/(2 ceil(log |A|))^(1/3) for sets of real numbers.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #52](https://www.erdosproblems.com/52), status: open ($250).

- [Bounding multiplicative energy by the sumset](https://arxiv.org/abs/0806.1040), József Solymosi (2009)

Parameters: `{"n": 20, "maximum": 10000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Quantify the impossibility of simultaneously small additive and multiplicative growth.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [An upper bound on the multiplicative energy](https://arxiv.org/abs/0806.1040): Main research objective: Quantify the impossibility of simultaneously small additive and multiplicative growth. Task connection: Exactly 20 distinct positive integers at most 10000, minimizing the maximum of sumset and product-set sizes. This uses integers rather than arbitrary reals, and includes diagonal pairs.

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

- paper: https://arxiv.org/abs/0806.1040 (József Solymosi, An upper bound on the multiplicative energy. Author abstract inspected: lower bounds on max(|A+A|,|AA|); the later publication has title Bounding multiplicative energy by the sumset.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000075 (JSP-000075; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Exactly 20 distinct positive integers at most 10000, minimizing the maximum of sumset and product-set sizes. This uses integers rather than arbitrary reals, and includes diagonal pairs.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
