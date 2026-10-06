# Large subsets of {1, ..., 1000} in which every sum has at most two representations (B2[2] sets)

**Source collection:** [Problem-bank constructions: hypergraphs, graph constructions and instance-solving methods: source-based research tasks](../../papers/science-prize_i.md)\
**Task id:** `science-b2-2-sets-1000`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> distinct integers in 1..1000 such that every integer has at most two representations a + b with a <= b from the set (exact count). Maximize the size. Sizes for N = 1000 are finite lower bounds for the extremal function (the asymptotic constant is at least 3/2); no finite optimum is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> distinct integers in 1..1000 such that every integer has at most two representations a + b with a <= b from the set (exact count). Maximize the size.

## State of the art

No documented optimum for N = 1000; asymptotically c_2 >= 3/2 (Cilleruelo, Ruzsa and Trujillo).

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #863](https://www.erdosproblems.com/863), status: proved.

- [Upper and Lower Bounds for Finite Bh[g] Sequences](https://doi.org/10.1006/jnth.2001.2767), Javier Cilleruelo, Imre Z. Ruzsa, Carlos Trujillo (2002)
- [Erdős Problem #863](https://www.erdosproblems.com/863)

Parameters: `{"n": 1000, "g": 2}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the maximal density c_2 of B2[2] sets, in which every integer has at most two representations as a sum of two elements (Erdős Problem #863).

Why it matters: B_h[g] sets generalize Sidon sets and are a basic object in additive combinatorics with open extremal constants.

- [Upper and Lower Bounds for Finite Bh[g] Sequences](https://doi.org/10.1006/jnth.2001.2767): Main research objective: Determine the maximal density c_2 of B2[2] sets, in which every integer has at most two representations as a sum of two elements (Erdős Problem #863). Task connection: Sizes for N = 1000 are finite lower bounds for the extremal function (the asymptotic constant is at least 3/2); no finite optimum is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Sizes for N = 1000 are finite lower bounds for the extremal function (the asymptotic constant is at least 3/2); no finite optimum is documented. Exact local certificates are not Lean proofs; reciprocal sums are reported as floats. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1006/jnth.2001.2767 (Javier Cilleruelo, Imre Z. Ruzsa and Carlos Trujillo, Upper and Lower Bounds for Finite Bh[g] Sequences (2002). Crossref record inspected; Erdős Problem #863 page inspected: for B2[r] sets |A| ~ c_r N^(1/2) with c_2 >= 3/2 from the Cilleruelo-Ruzsa-Trujillo construction, while the difference analogue has c'_r <= sqrt(r), so c_r != c'_r (resolved). No finite maxima for N = 1000 are documented. Sizes for N = 1000 are finite lower bounds for the extremal function (the asymptotic constant is at least 3/2); no finite optimum is documented.)
- archive: https://www.erdosproblems.com/863 (Erdős Problem #863 (proved); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000156 (JSP-000156; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- No documented value for N = 1000 (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
