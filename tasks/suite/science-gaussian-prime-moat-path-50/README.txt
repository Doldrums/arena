# Gaussian-prime paths with small maximum jumps

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-gaussian-prime-moat-path-50`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> a list of distinct integer coordinate pairs in [-64,64]^2, starting at (1,1), ending with max(abs(x),abs(y))>=50, and containing only Gaussian primes. Minimize the largest squared Euclidean step. Axis primes must be 3 modulo 4; off-axis norms must be prime. The finite path minimizes its largest jump inside a bounded square; it does not establish an infinite path or reproduce the periodic-moat proof. The optimum is 8, found by breadth-first search over all Gaussian primes in the box; this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a list of distinct integer coordinate pairs in [-64,64]^2, starting at (1,1), ending with max(abs(x),abs(y))>=50, and containing only Gaussian primes. Minimize the largest squared Euclidean step. Axis primes must be 3 modulo 4; off-axis norms must be prime.

## State of the art

With steps of squared length at most 5, the Gaussian primes reachable from 1+i stay inside max(|x|,|y|) < 50, while squared length 8 suffices. A breadth-first search over all Gaussian primes in [-64,64]^2 (scripts/check_state_of_the_art.py) gives the optimum 8. Whether a walk with bounded steps can reach infinity is the Gaussian moat problem (Erdős Problem #952).

Reference value: proven optimum `8` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #952](https://www.erdosproblems.com/952), status: open.

- [Periodic Gaussian Moats](https://doi.org/10.1080/10586458.1997.10504616), Ellen Gethner, H. M. Stark (1997)

Parameters: `{"bound": 64, "target": 50}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand the existence of bounded-step walks through Gaussian primes.

Why it matters: Explicit paths provide finite evidence about connectivity in the Gaussian primes, the number-theoretic question studied by Gethner and Stark.

- [Periodic Gaussian Moats](https://doi.org/10.1080/10586458.1997.10504616): Main research objective: Understand the existence of bounded-step walks through Gaussian primes. Task connection: The finite path minimizes its largest jump inside a bounded square; it does not establish an infinite path or reproduce the periodic-moat proof.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The finite path minimizes its largest jump inside a bounded square; it does not establish an infinite path or reproduce the periodic-moat proof. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1080/10586458.1997.10504616 (Ellen Gethner and H. M. Stark, Periodic Gaussian Moats (1997). Publisher-indexed abstract inspected; direct page returned HTTP 403. The abstract studies bounded-step Gaussian-prime walks and periodic moats. It attributes the question to Gordon. The finite path minimizes its largest jump inside a bounded square; it does not establish an infinite path or reproduce the periodic-moat proof.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0701-0800.md#JSP-000792 (JSP-000792; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- Solved finite case: With steps of squared length at most 5, the Gaussian primes reachable from 1+i stay inside max(|x|,|y|) < 50, while squared length 8 suffices.
- The finite endpoint and coordinate bounds cannot resolve the infinite Gaussian moat problem. The elementary two-point starter is locally chosen, not a published record.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
