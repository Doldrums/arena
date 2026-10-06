# Hadamard matrix constructions through order 100

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-hadamard-matrices-orders-through-100`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 25 rows for orders 4,8,...,100. A row is None or an n-by-n matrix of Python integer signs -1/+1 satisfying H*H^T=n*I. Maximize the fraction of orders constructed. Every row product is checked exactly. These small orders have known solutions; this is a rediscovery task. Construct sign matrices for orders 4,8,...,100, maximizing order coverage. These orders already have constructions; no SageMath code or matrix data is copied.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 25 rows for orders 4,8,...,100. A row is None or an n-by-n matrix of Python integer signs -1/+1 satisfying H*H^T=n*I. Maximize the fraction of orders constructed. Every row product is checked exactly. These small orders have known solutions; this is a rediscovery task.

## State of the art

Hadamard matrices of every order 4k up to 664 are known (668 is the smallest open order), so all 25 orders up to 100 can be constructed. Order 92 was the last of them, found by Baumert, Golomb and Hall.

Reference value: proven optimum `1.0` (reviewed 2026-09-24).

- [A database of constructions of Hadamard matrices](https://arxiv.org/abs/2411.18897), Matteo Cati, Dmitrii V. Pasechnik (2024)
- [Discovery of an Hadamard matrix of order 92](https://doi.org/10.1090/s0002-9904-1962-10761-7), Leonard Baumert, S. W. Golomb, Marshall Hall (1962)
- [A Hadamard matrix of order 428](https://doi.org/10.1002/jcd.20043), H. Kharaghani, B. Tayfeh-Rezaie (2005)

Parameters: `{"maximum": 100}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct and verify Hadamard matrices across admissible orders.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [A database of constructions of Hadamard matrices](https://arxiv.org/abs/2411.18897): Main research objective: Construct and verify Hadamard matrices across admissible orders. Task connection: Construct sign matrices for orders 4,8,...,100, maximizing order coverage. These orders already have constructions; no SageMath code or matrix data is copied.

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

- paper: https://arxiv.org/abs/2411.18897 (Matteo Cati and Dmitrii V. Pasechnik, A database of constructions of Hadamard matrices. Author abstract and HTML v2 Sections 1 and 4.2 inspected: exact orthogonal-sign definition, known construction database, and Sylvester construction attribution.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0001-0100.md#JSP-000013 (JSP-000013; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Construct sign matrices for orders 4,8,...,100, maximizing order coverage. These orders already have constructions; no SageMath code or matrix data is copied.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
