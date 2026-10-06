# Few cycle lengths under degree and girth constraints

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-girth-degree-cycle-length-diversity`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> undirected simple edges on vertices 0..11. Every vertex must have degree at least three and every simple cycle must have length at least four. Enumerating every simple cycle, the evaluator minimizes the number of distinct cycle lengths. Disconnected graphs are allowed by the source problem. The local n=12 minimum-degree-three condition is stronger than the paper’s average-degree-three hypothesis. Exhaustive cycles prove the local score, without proving any general lower bound or current extremal record.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> undirected simple edges on vertices 0..11. Every vertex must have degree at least three and every simple cycle must have length at least four. Enumerating every simple cycle, the evaluator minimizes the number of distinct cycle lengths. Disconnected graphs are allowed by the source problem.

## State of the art

No value is published for this instance, which was fixed for this dataset; the task compares search methods. Benny Sudakov and Jacques Verstraëte (2007, Cycle lengths in sparse graphs) study the underlying problem.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

- [Cycle lengths in sparse graphs](https://arxiv.org/abs/0707.2117), Benny Sudakov and Jacques Verstraëte (2007)

Parameters: `{"n": 12, "minimum_degree": 3, "girth": 4}`

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Relate sparse-graph degree and girth to the diversity of cycle lengths.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Benny Sudakov and Jacques Verstraëte, Cycle lengths in sparse graphs (2007 preprint; 2008 publication)](https://arxiv.org/abs/0707.2117): Main research objective: Relate sparse-graph degree and girth to the diversity of cycle lengths. Task connection: The local n=12 minimum-degree-three condition is stronger than the paper’s average-degree-three hypothesis. Exhaustive cycles prove the local score, without proving any general lower bound or current extremal record.

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

- paper: https://arxiv.org/abs/0707.2117 (Benny Sudakov and Jacques Verstraëte, Cycle lengths in sparse graphs (2007 preprint; 2008 publication). Abstract: minimum possible number of distinct cycle lengths at given average degree and girth; the first part proves an Erdős conjecture.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000619 (JSP-000619; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The local n=12 minimum-degree-three condition is stronger than the paper’s average-degree-three hypothesis. Exhaustive cycles prove the local score, without proving any general lower bound or current extremal record.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
