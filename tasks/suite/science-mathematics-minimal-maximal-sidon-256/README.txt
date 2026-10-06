# Small inclusion-maximal Sidon sets in [1,256]

**Source collection:** [Prize-listed mathematical problems: source-based research tasks](../../papers/science-prize.md)\
**Task id:** `science-mathematics-minimal-maximal-sidon-256`\
**Protocol:** `recreated_verified`\
**Direction:** minimize\

## Task

Construct a Sidon subset of the integer interval [1,256] that cannot be extended by any other interval element, and minimize its cardinality. The verifier checks every unordered pair sum including diagonal pairs and tries every missing element. This is the N=256 instance of the minimal-size maximal-set problem listed as JSP-000154, distinct from the existing maximum-cardinality Sidon-set task.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

construct() -> a nonempty list of distinct Python integers in [1,N]. All unordered sums a+b with a<=b must be distinct INCLUDING a=a. Adding ANY missing integer from [1,N] must destroy this property. Minimize cardinality. Fixed N=256 is a finite adaptation of the small maximal Sidon-set problem; maximal means inclusion-maximal, not maximum cardinality.

Parameters: `{"n": 256}`

## Labels

Scientific contribution: `open_problem` (tier 1); artifact `construction`, domain `mathematics`, data `none`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `mathematics`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Construct small inclusion-maximal Sidon subsets of finite integer intervals.

Why it matters: Ruzsa's primary paper explicitly constructs small maximal Sidon sets in [1,N]; the task directly studies that extremal quantity at one finite N.

- [A Small Maximal Sidon Set](https://link.springer.com/article/10.1023/A:1009757824153): Main research objective: Construct small Sidon sets in [1,N] that cannot be extended while retaining the Sidon property. Task connection: The local N=256 cardinality minimization uses the same maximality definition. Its greedy seed and exhaustive verifier are independently written; the asymptotic construction and theorem are not reproduced.

Primary publisher abstract states the construction objective and maximality definition. Full text is subscription restricted; author-hosted Dias da Silva–Nathanson paper independently clarifies repeated-element sums.

## Evaluation protocol

Locally implemented evaluator with recorded reference checks; consult the task-specific tests and evidence for their exact scope. This label alone does not establish reproduction of the paper's full experiment.

- This MINIMIZES an inclusion-maximal Sidon set, unlike the existing maximum-cardinality Sidon task. Every missing element is tested, with diagonal sums included. No Ruzsa construction code is reused and no asymptotic bound, optimality or Lean proof is claimed.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Sources

- paper: https://link.springer.com/article/10.1023/A:1009757824153 (Imre Z. Ruzsa, A Small Maximal Sidon Set, Ramanujan Journal 2 (1998), pp.55–58. Small inclusion-maximal Sidon sets in [1,N]; local exhaustive verifier and greedy seed do not reproduce Ruzsa's asymptotic construction. Primary publisher abstract and bibliography inspected; full text subscription restricted.)
- paper: https://www.theoryofnumbers.com/melnathanson/pdfs/nath2009-132.pdf (J. A. Dias da Silva and Melvyn B. Nathanson, Maximal Sidon sets and matroids (2009), section 1. Sidon definition includes multisets (repeated elements); the example {1,3,4} is maximal in [1,7] despite a larger Sidon set existing.)
- benchmark: https://github.com/TheJustinSunPrize/awards/blob/bcf1866ea9a4ae82b32bd95b82ffd812b9ee80d2/problems/catalog-0101-0200.md#JSP-000154 (JSP-000154: smallest cardinality of inclusion-maximal Sidon sets; N=256 resource-bounded instance chosen locally.)

## Limitations

- These are independently implemented finite certificate/search tasks. They are not Lean proofs, prize submissions, full general-conjecture solutions, or claims of eligibility or mathematical novelty.
- The prize catalog is a discovery source whose statements and contributor records can change. The pinned revision is recorded; original mathematical authorship is separate from this local implementation.
- Candidate Python code is trusted code; the evaluator process is not a security sandbox.
- An accepted set establishes feasibility and an upper bound on the minimum cardinality for N=256. It does not prove optimality or resolve the general asymptotic problem.
- Repeated-element sums a+a are included. Maximal means no strict Sidon superset in the interval; it does not mean maximum size.
- The ascending greedy baseline is local code. No construction coordinates, implementation, or algorithm from Ruzsa's paper are imported.
