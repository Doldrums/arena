# Long coprimality gaps for five-prime moduli

**Source collection:** [Problem-bank constructions: geometry and discrete structures: source-based research tasks](../../papers/science-prize_d.md)\
**Task id:** `science-jacobsthal-five-prime-gaps`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> a squarefree integer n in [2,1000000] with exactly five distinct prime factors. Maximize the longest cyclic run of residues not coprime to n. This score equals j(n)-1, not j(n); every residue and the wraparound gap are checked. The bounded five-factor search recovers a known finite case; Table 1 gives H(5)=14, so the local run-length score has a known upper bound of 13.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a squarefree integer n in [2,1000000] with exactly five distinct prime factors. Maximize the longest cyclic run of residues not coprime to n. This score equals j(n)-1, not j(n); every residue and the wraparound gap are checked.

## State of the art

Hajdu and Saradha proved H(5) = 14. The longest run of residues not coprime to a squarefree n with five prime factors is therefore at most 13, and 2310 = 2·3·5·7·11 attains it.

Reference value: proven optimum `13` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #970](https://www.erdosproblems.com/970), status: open.

- [Disproof of a conjecture of Jacobsthal](https://doi.org/10.1090/S0025-5718-2012-02581-6), Lajos Hajdu, N. Saradha (2012)

Parameters: `{"maximum": 1000000, "prime_count": 5}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine extremal Jacobsthal values at fixed distinct-prime-factor counts.

Why it matters: Extremal gaps between reduced residues are directly studied in the cited number-theory paper; this small case is explicitly a rediscovery exercise.

- [Disproof of a conjecture of Jacobsthal](https://doi.org/10.1090/S0025-5718-2012-02581-6): Main research objective: Determine extremal Jacobsthal values at fixed distinct-prime-factor counts. Task connection: The bounded five-factor search recovers a known finite case; Table 1 gives H(5)=14, so the local run-length score has a known upper bound of 13.

Primary research directly studies this mathematical objective; finite scope and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- The bounded five-factor search recovers a known finite case; Table 1 gives H(5)=14, so the local run-length score has a known upper bound of 13. Exact local certificates are not Lean proofs. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1090/S0025-5718-2012-02581-6 (Lajos Hajdu and N. Saradha, Disproof of a conjecture of Jacobsthal (2012). Author-hosted full text, introduction and Theorem 1.2/Table 1 inspected. It defines H(r), proves H(5)=14, and distinguishes the longest bad run from j(n). The bounded five-factor search recovers a known finite case; Table 1 gives H(5)=14, so the local run-length score has a known upper bound of 13.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0801-0900.md#JSP-000804 (JSP-000804; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the paper above.)

## Limitations

- The five-prime case is already resolved: H(5)=14. Neither a record here nor failure to improve a seed is progress on an unrestricted quadratic bound.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
