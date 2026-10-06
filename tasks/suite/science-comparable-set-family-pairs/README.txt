# Many comparable pairs in a fixed-size set family

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-comparable-set-family-pairs`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> exactly forty distinct subsets of vertices 0..11, each as a list of distinct integers; the empty set is allowed. Maximize the number of unordered pairs in which one member is a strict subset of the other. The local parameters are n=12 and m=40. This is a finite lower-bound construction for c(12,40); the baseline consists of the first forty binary masks and does not copy the paper’s extremal constructions.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly forty distinct subsets of vertices 0..11, each as a list of distinct integers; the empty set is allowed. Maximize the number of unordered pairs in which one member is a strict subset of the other.

## State of the art

No documented value of c(12, 40). Alon, Das, Glebov and Sudakov determine the extremal families only asymptotically or for special sizes (towers of subcubes); the related Erdős Problem #777 is solved.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #777](https://www.erdosproblems.com/777), status: solved.

- [Comparable pairs in families of sets](https://doi.org/10.1016/j.jctb.2015.05.009), Noga Alon, Shagnik Das, Roman Glebov, Benny Sudakov (2015)

Parameters: `{"n": 12, "m": 40}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how concentrated comparability can be in a set family of prescribed size.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Noga Alon, Shagnik Das, Roman Glebov and Benny Sudakov, Comparable pairs in families of sets (2015)](https://www.tau.ac.il/~nogaa/PDFS/compairs1.pdf): Main research objective: Determine how concentrated comparability can be in a set family of prescribed size. Task connection: The local parameters are n=12 and m=40. This is a finite lower-bound construction for c(12,40); the baseline consists of the first forty binary masks and does not copy the paper’s extremal constructions.

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

- paper: https://www.tau.ac.il/~nogaa/PDFS/compairs1.pdf (Noga Alon, Shagnik Das, Roman Glebov and Benny Sudakov, Comparable pairs in families of sets (2015). Abstract and section 1.1 define c(n,m) as the maximum number of comparable pairs in an m-member family of subsets of [n].)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000637 (JSP-000637; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The local parameters are n=12 and m=40. This is a finite lower-bound construction for c(12,40); the baseline consists of the first forty binary masks and does not copy the paper’s extremal constructions.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
