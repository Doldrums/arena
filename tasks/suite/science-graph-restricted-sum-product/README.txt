# Small sums and products along selected graph edges

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-graph-restricted-sum-product`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> {'values': fourteen distinct positive integers <=10000, 'edges': exactly 35 simple undirected edges on their indices}. Minimize max(number of distinct edge sums, number of distinct edge products). Only edges between different vertices count. The local restrictions are fourteen positive integer labels, 35 edges and label cap 10000. The max objective is stated explicitly; this does not reproduce the paper’s asymptotic graph constructions or claim a new counterexample.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'values': fourteen distinct positive integers <=10000, 'edges': exactly 35 simple undirected edges on their indices}. Minimize max(number of distinct edge sums, number of distinct edge products). Only edges between different vertices count.

## State of the art

No documented value for fourteen labels and 35 edges. Alon, Ruzsa and Solymosi disproved the strong form of the conjecture (Erdős Problem #808). They also proved max(|A+_G A|, |A·_G A|) >> m^(3/2) n^(-7/4) for m edges.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #808](https://www.erdosproblems.com/808), status: disproved.

- [Sums, products and ratios along the edges of a graph](https://arxiv.org/abs/1802.06405), Noga Alon, Imre Ruzsa, József Solymosi (2020)

Parameters: `{"n": 14, "m": 35, "maximum": 10000}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Understand simultaneous additive and multiplicative structure when observations are restricted to graph edges.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Noga Alon, Imre Ruzsa and József Solymosi, Sums, products and ratios along the edges of a graph (2018 preprint; 2020 publication)](https://arxiv.org/abs/1802.06405): Main research objective: Understand simultaneous additive and multiplicative structure when observations are restricted to graph edges. Task connection: The local restrictions are fourteen positive integer labels, 35 edges and label cap 10000. The max objective is stated explicitly; this does not reproduce the paper’s asymptotic graph constructions or claim a new counterexample.

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

- paper: https://arxiv.org/abs/1802.06405 (Noga Alon, Imre Ruzsa and József Solymosi, Sums, products and ratios along the edges of a graph (2018 preprint; 2020 publication). Author abstract and introduction study simultaneous sumset/product-set sizes restricted to graph edges, including constructions disproving the strongest conjecture.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000665 (JSP-000665; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- The local restrictions are fourteen positive integer labels, 35 edges and label cap 10000. The max objective is stated explicitly; this does not reproduce the paper’s asymptotic graph constructions or claim a new counterexample.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
