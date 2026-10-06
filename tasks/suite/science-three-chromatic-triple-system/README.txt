# Few hyperedges forcing three colors

**Source collection:** [Problem-bank constructions: graphs and set systems: source-based research tasks](../../papers/science-prize_c.md)\
**Task id:** `science-three-chromatic-triple-system`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

construct() -> {'edges': distinct triples on 0..8, 'colors': nine labels from 0..2}. Every edge must be nonmonochromatic in the provided coloring. The evaluator exhaustively rejects any hypergraph admitting a two-coloring. Minimize edge count among exactly three-chromatic triple systems. This is a rediscovery task: the literature states the optimum f(3,3)=7, attainable within nine vertices. The ten-edge complete-triple-system baseline can improve to that known optimum; no mathematical novelty is asserted.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> {'edges': distinct triples on 0..8, 'colors': nine labels from 0..2}. Every edge must be nonmonochromatic in the provided coloring. The evaluator exhaustively rejects any hypergraph admitting a two-coloring. Minimize edge count among exactly three-chromatic triple systems.

## State of the art

The Fano plane is a 3-uniform hypergraph with 7 edges that is not 2-colourable, while every triple system with at most 6 edges is 2-colourable. Hence f(3,3) = 7, as stated by Alon. Erdős Problem #832, the general edge count for large chromatic number, was disproved.

Reference value: proven optimum `7` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #832](https://www.erdosproblems.com/832), status: disproved.

- [Hypergraphs with high chromatic number](https://doi.org/10.1007/bf02582966), Noga Alon (1985)

Parameters: `{"n": 9, "r": 3, "colors": 3}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the minimum number of uniform hyperedges required to force a prescribed chromatic number.

Why it matters: The cited paper investigates this mathematical problem as a research objective. The task evaluates a finite construction or certificate for the same quantity, with the local restriction stated explicitly.

- [Noga Alon, Hypergraphs with High Chromatic Number (1985)](https://www.cs.tau.ac.il/~nogaa/PDFS/Publications/Hypergraphs%20with%20high%20chromatic%20number.pdf): Main research objective: Determine the minimum number of uniform hyperedges required to force a prescribed chromatic number. Task connection: This is a rediscovery task: the literature states the optimum f(3,3)=7, attainable within nine vertices. The ten-edge complete-triple-system baseline can improve to that known optimum; no mathematical novelty is asserted.

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

- paper: https://www.cs.tau.ac.il/~nogaa/PDFS/Publications/Hypergraphs%20with%20high%20chromatic%20number.pdf (Noga Alon, Hypergraphs with High Chromatic Number (1985). Page 387 defines f(k,s), gives the complete-uniform construction, and explicitly states f(3,3)=7 using the Fano plane.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0601-0700.md#JSP-000688 (JSP-000688; pinned revision bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2. Independently paraphrased finite adaptation; catalog contributor claims are not accepted as proof.)

## Limitations

- Independent finite computational adaptation. Not a Lean proof, prize submission, general conjecture solution, or guarantee of novelty.
- This is a rediscovery task: the literature states the optimum f(3,3)=7, attainable within nine vertices. The ten-edge complete-triple-system baseline can improve to that known optimum; no mathematical novelty is asserted.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
