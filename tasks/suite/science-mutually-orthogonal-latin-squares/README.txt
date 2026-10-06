# Mutually orthogonal Latin squares of order ten

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-mutually-orthogonal-latin-squares`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a nonempty list of 10-by-10 arrays with Python integer symbols 0..9. Every row and column must contain each symbol exactly once. For every two arrays, their 100 ordered symbol pairs must be distinct. Maximize the number of pairwise orthogonal arrays. Only order ten is evaluated. The cyclic single-square baseline does not implement Wilson’s recursive constructions. No current best-known N(10), global optimality or novel family is asserted.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty list of 10-by-10 arrays with Python integer symbols 0..9. Every row and column must contain each symbol exactly once. For every two arrays, their 100 ordered symbol pairs must be distinct. Maximize the number of pairwise orthogonal arrays.

## State of the art

Two orthogonal Latin squares of order 10 exist (Parker 1959), and no set of three has been found. Since there is no projective plane of order 10 (Lam, Thiel and Swiercz 1989), at most 8 are possible. The growth of N(n) is Erdős Problem #724.

Reference value: best known value `2` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #724](https://www.erdosproblems.com/724), status: open.

- [Orthogonal Latin squares](https://doi.org/10.1073/pnas.45.6.859), E. T. Parker (1959)
- [The Non-Existence of Finite Projective Planes of Order 10](https://doi.org/10.4153/cjm-1989-049-4), C. W. H. Lam, L. Thiel, S. Swiercz (1989)
- [Concerning the number of mutually orthogonal latin squares](https://doi.org/10.1016/0012-365X(74)90148-4), Richard M. Wilson (1974)

Parameters: `{"n": 10}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine attainable numbers of mutually orthogonal Latin squares, a central design-theory construction problem.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Richard M. Wilson, Concerning the number of mutually orthogonal latin squares (1974)](https://doi.org/10.1016/0012-365X(74)90148-4): Main research objective: Determine attainable numbers of mutually orthogonal Latin squares, a central design-theory construction problem. Task connection: Only order ten is evaluated. The cyclic single-square baseline does not implement Wilson’s recursive constructions. No current best-known N(10), global optimality or novel family is asserted.

Supported by the inspected primary problem statement, rather than the prize listing or an agent benchmark. Finite progress is not automatically a novel scientific result.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Exact finite certificate validation; independently implemented from the cited mathematical definition. Resource bounds and source adaptation are recorded per task. No Lean verification or general theorem is claimed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/0012-365X(74)90148-4 (Richard M. Wilson, Concerning the number of mutually orthogonal latin squares (1974). Publisher abstract defines N(n), the maximum size of a mutually orthogonal family, and proves general lower bounds through combinatorial constructions.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0501-0600.md#JSP-000592 (JSP-000592; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- Only order ten is evaluated. The cyclic single-square baseline does not implement Wilson’s recursive constructions. No current best-known N(10), global optimality or novel family is asserted.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
