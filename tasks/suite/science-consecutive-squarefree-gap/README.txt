# Large gaps between consecutive squarefree integers

**Source collection:** [Problem-bank constructions: additive combinatorics: source-based research tasks](../../papers/science-prize_a.md)\
**Task id:** `science-consecutive-squarefree-gap`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> [a,b], positive squarefree endpoints a<b<=maximum=10000000, with b-a<=10000. EVERY interior integer must be nonsquarefree. Maximize b-a. Endpoints and every interior integer are tested exactly. Maximize the gap between consecutive positive squarefree endpoints at most 10000000, with gap at most 10000. Endpoints and every interior integer are checked. The optimum is 10 (8870023 to 8870033; OEIS A020754); this is a rediscovery task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> [a,b], positive squarefree endpoints a<b<=maximum=10000000, with b-a<=10000. EVERY interior integer must be nonsquarefree. Maximize b-a. Endpoints and every interior integer are tested exactly.

## State of the art

The largest gap between consecutive squarefree numbers up to 10^7 is 10, from 8870023 to 8870033. The next record gap starts at 221167421 (OEIS A020754), and a sieve up to 10^7 recomputes the value.

Reference value: proven optimum `10` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #208](https://www.erdosproblems.com/208), status: open.

- [OEIS A020754: Increasing gaps between squarefree numbers (lower end)](https://oeis.org/A020754)
- [Explicit bounds for large gaps between squarefree integers](https://arxiv.org/abs/2211.09975), Angel Kumchev, Wade McCormick, Nathan McNew, Ariana Park, Russell Scherr, Willow Ziehr (2023)

Parameters: `{"maximum": 10000000, "maximum_gap": 10000}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Bound the gaps between consecutive squarefree integers.

Why it matters: The finite certificates expose exact extremal constructions for the mathematical question studied in the source, with adaptation limits stated separately.

- [Explicit bounds for large gaps between squarefree integers](https://arxiv.org/abs/2211.09975): Main research objective: Bound the gaps between consecutive squarefree integers. Task connection: Maximize the gap between consecutive positive squarefree endpoints at most 10000000, with gap at most 10000. Endpoints and every interior integer are checked.

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

- paper: https://arxiv.org/abs/2211.09975 (Angel Kumchev, Wade McCormick, Nathan McNew, Ariana Park, Russell Scherr and Willow Ziehr, Explicit bounds for large gaps between squarefree integers. Author abstract inspected, including all six authors and explicit gap bounds.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000193 (JSP-000193; pinned discovery record, independently paraphrased. Source wording and paper-specific differences are explained in limitations.)

## Limitations

- Solved finite case: The largest gap between consecutive squarefree numbers up to 10^7 is 10, from 8870023 to 8870033.
- Maximize the gap between consecutive positive squarefree endpoints at most 10000000, with gap at most 10000. Endpoints and every interior integer are checked.
- All computations are bounded. A valid certificate is not an optimality proof, new theorem, Lean proof, or evidence of prize eligibility. Candidate Python is trusted research code.
