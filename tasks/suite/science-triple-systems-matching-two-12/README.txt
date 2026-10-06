# Triple systems on 12 points without three disjoint triples

**Source collection:** [Problem-bank constructions: extremal graphs, hypergraphs and designs: source-based research tasks](../../papers/science-prize_f.md)\
**Task id:** `science-triple-systems-matching-two-12`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> list of distinct triples [a, b, c] of distinct points in 0..11 containing no three pairwise disjoint triples. Maximize the number of triples; the proven optimum is 100. For n = 12 and s = 2 the maximum is max{56, 100} = 100, attained by all triples meeting two fixed points.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> list of distinct triples [a, b, c] of distinct points in 0..11 containing no three pairwise disjoint triples. Maximize the number of triples; the proven optimum is 100.

## State of the art

Maximum 100 = C(12,3) - C(10,3) by Frankl's theorem for triple systems.

Reference value: proven optimum `100` (reviewed 2026-09-24).

- [On the maximum number of edges in a hypergraph with given matching number](https://doi.org/10.1016/j.dam.2016.08.003), Peter Frankl (2017)

Parameters: `{"n": 12, "matching": 2}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Prove the Erdős matching conjecture for triple systems.

Why it matters: The Erdős matching conjecture is a central open problem for general uniformity; the 3-uniform case solved by Frankl gives an exact finite target.

- [On the maximum number of edges in a hypergraph with given matching number](https://doi.org/10.1016/j.dam.2016.08.003): Main research objective: Prove the Erdős matching conjecture for triple systems. Task connection: For n = 12 and s = 2 the maximum is max{56, 100} = 100, attained by all triples meeting two fixed points.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- For n = 12 and s = 2 the maximum is max{56, 100} = 100, attained by all triples meeting two fixed points. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1016/j.dam.2016.08.003 (Peter Frankl, On the maximum number of edges in a hypergraph with given matching number (2017). Crossref record and abstract inspected: the maximum number of edges of a 3-uniform hypergraph on n vertices with matching number s is max{C(3s+2,3), C(n,3)-C(n-s,3)} for n >= 3s+2. For n = 12 and s = 2 the maximum is max{56, 100} = 100, attained by all triples meeting two fixed points.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000850 (JSP-000850; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; the extremal family is elementary once known.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
