# Contact numbers of 32 unit pennies on the triangular lattice

**Source collection:** [Problem-bank constructions: discrete geometry and analysis: source-based research tasks](../../papers/science-prize_g.md)\
**Task id:** `science-penny-graph-contacts-32`\
**Protocol:** `recreated_verified`\
**Direction:** maximize\

## Task

construct() -> exactly 32 distinct integer pairs [a, b] with |a|, |b| <= 64 denoting lattice points a + b*omega, omega = exp(i*pi/3), which are at mutual distance at least one. Maximize the number of pairs at distance exactly one; Harborth's theorem gives the optimum floor(3n - sqrt(12n - 3)) = 76. Harborth's formula gives 76 for n = 32 and triangular-lattice spirals attain it, so the lattice restriction loses nothing.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> exactly 32 distinct integer pairs [a, b] with |a|, |b| <= 64 denoting lattice points a + b*omega, omega = exp(i*pi/3), which are at mutual distance at least one. Maximize the number of pairs at distance exactly one; Harborth's theorem gives the optimum floor(3n - sqrt(12n - 3)) = 76.

## State of the art

Harborth (1974): the maximum number of unit distances among n points at mutual distance >= 1 is floor(3n - sqrt(12n - 3)) = 76 for n = 32.

Reference value: proven optimum `76` (reviewed 2026-09-24).

Underlying problem: [Erdős Problem #1084](https://www.erdosproblems.com/1084), status: open (solved in the plane by Harborth).

- [Erdős Problem #1084](https://www.erdosproblems.com/1084)
- [Contact Numbers for Sphere Packings](https://doi.org/10.1007/978-3-662-57413-3_2), Károly Bezdek, Muhammad A. Khan (2018)

Parameters: `{"n": 32, "bound": 64}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `published_value`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Determine the maximum number of touching pairs among n non-overlapping unit disks (and spheres).

Why it matters: Contact numbers (Erdős Problem #1084) are solved in the plane but open in three dimensions; the planar case is a calibrated rediscovery.

- [Contact Numbers for Sphere Packings](https://doi.org/10.1007/978-3-662-57413-3_2): Main research objective: Determine the maximum number of touching pairs among n non-overlapping unit disks (and spheres). Task connection: Harborth's formula gives 76 for n = 32 and triangular-lattice spirals attain it, so the lattice restriction loses nothing.

Primary research directly studies this mathematical objective; the finite scope, reference value and rediscovery status are explicit.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- Harborth's formula gives 76 for n = 32 and triangular-lattice spirals attain it, so the lattice restriction loses nothing. Exact local certificates are not Lean proofs; floating-point scores are stated as such. Consult the independent oracle and malformed-input tests.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://doi.org/10.1007/978-3-662-57413-3_2 (Károly Bezdek and Muhammad A. Khan, Contact Numbers for Sphere Packings (2018). Crossref record inspected; Erdős Problem #1084 page inspected: Harborth (1974) proved f_2(n) = floor(3n - sqrt(12n - 3)) for points at mutual distance at least one, attained by triangular-lattice spirals. Harborth's formula gives 76 for n = 32 and triangular-lattice spirals attain it, so the lattice restriction loses nothing.)
- archive: https://www.erdosproblems.com/1084 (Erdős Problem #1084 (open (solved in the plane by Harborth)); statement, history and current bounds reviewed 2026-09-24.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0901-1000.md#JSP-000901 (JSP-000901; pinned discovery source, independently paraphrased. Primary mathematical attribution follows the papers above.)

## Limitations

- Solved finite case; candidates are restricted to the triangular lattice, which contains optimal configurations.
- Independent Python implementation; no paper text, upstream evaluator, Lean proof or prize-bank content is redistributed. Candidate Python executes as trusted research code.
