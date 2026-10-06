# Sixteen frequencies whose cosine sum stays shallow (Chowla's cosine problem)

**Source collection:** [Problem-bank constructions: discrete geometry and analysis: source-based research tasks](../../papers/science-prize_g.md)\
**Task id:** `science-chowla-cosine-sixteen-frequencies`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> 16 distinct integers in 1..200. The score is min over theta of sum cos(a*theta), divided by sqrt(16), computed by dense sampling of the full circle and golden-section refinement of the deepest local minima (accuracy about 1e-9). Maximize (make the minimum as shallow as possible). Shallow minima for 16 frequencies probe the finite side of Chowla's problem; no finite optimum is documented.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> 16 distinct integers in 1..200. The score is min over theta of sum cos(a*theta), divided by sqrt(16), computed by dense sampling of the full circle and golden-section refinement of the deepest local minima (accuracy about 1e-9). Maximize (make the minimum as shallow as possible).

## State of the art

No documented optimum for 16 frequencies; every set has minimum below -c N^(1/7) (Bedert 2025) and N^(1/2) is the conjectured order.

Reference value: no documented value for this finite instance (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #510](https://www.erdosproblems.com/510), status: open.

- [Negative values of cosine sums](https://doi.org/10.4064/aa111-2-6), Imre Z. Ruzsa (2004)
- [Polynomial bounds for the Chowla Cosine Problem](https://arxiv.org/abs/2509.05260), B. Bedert (2025)

Parameters: `{"k": 16, "maximum": 200}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine how negative a cosine sum over N distinct frequencies must become.

Why it matters: Chowla's cosine problem (Erdős Problem #510; Green's problem 81) saw polynomial bounds only in 2025.

- [Negative values of cosine sums](https://doi.org/10.4064/aa111-2-6): Main research objective: Determine how negative a cosine sum over N distinct frequencies must become. Task connection: Shallow minima for 16 frequencies probe the finite side of Chowla's problem; no finite optimum is documented.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Shallow minima for 16 frequencies probe the finite side of Chowla's problem; no finite optimum is documented. Exact local certificates are not Lean proofs; floating-point scores are stated as such. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.4064/aa111-2-6 (Imre Z. Ruzsa, Negative values of cosine sums (2004). Crossref record inspected; Erdős Problem #510 page inspected: every N-element set has theta with sum cos(n theta) < -c N^(1/7) (Bedert 2025; Jin, Milojević, Tomon and Zhang independently polynomial), while A = B - B for Sidon B shows N^(1/2) would be best possible. Shallow minima for 16 frequencies probe the finite side of Chowla's problem; no finite optimum is documented.)
- archive: https://www.erdosproblems.com/510 (Erdős Problem #510 (open); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0401-0500.md#JSP-000409 (JSP-000409; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Floating-point score with sampling refinement; no documented finite value (reference label none).
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
