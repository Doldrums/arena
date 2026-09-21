# Theoretical computer science: Exact XOR-circuit synthesis

**Source collection:** [Algorithms and theoretical computer science: source-based research tasks](../../papers/science-tcs_expansion.md)\
**Task id:** `science-tcs-xor-circuit-synthesis`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Exact XOR-circuit synthesis under a bounded candidate interface with independent verification; generated mathematical instances, no external dataset.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

synthesize(matrix, depth_limit) -> {'gates': [[wire, wire], ...], 'outputs': [wire,...]}. Input wires are 0..n-1, constant-zero wire is n, gate k (zero-based) produces wire n+1+k. Exact symbolic GF(2) verification; depth <=16. Minimize mean gate-count / independent-row baseline over 8x8,12x16,16x16 binary maps.

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Minimize the number of XOR gates needed to implement a specified binary linear transformation.

Why it matters: Reducing linear-circuit complexity is a central component of the cited circuit-minimization research.

- [A New Combinational Logic Minimization Technique with Applications to Cryptology](https://www.nist.gov/publications/new-combinational-logic-minimization-technique-applications-cryptology): Main research objective: Reduce combinational circuit size, including the gate cost of linear transformations used in cryptographic implementations. Task connection: The local task isolates XOR straight-line synthesis for generated GF(2) matrices and verifies exact equivalence. It omits nonlinear gates and full cryptographic designs, so it does not establish an AES implementation improvement.

Circuit minimization is a substantive engineering and theoretical-computing target of the source, not merely an example supplied to a generic agent.

## Evaluation protocol

Locally authored implementation of the cited scientific task. Source data, generated mathematical instances, reference checks and adaptations are specified below; unit-test fixtures do not establish a benchmark reproduction.

- Native bounded research instances derived from the cited mathematical model, not an upstream benchmark-score reproduction. Public seeds are development instances; freeze candidates and use new graph/stream/matrix families for independent generalization.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://www.nist.gov/publications/new-combinational-logic-minimization-technique-applications-cryptology (Boyar and Peralta: straight-line XOR circuits for linear maps over GF(2).)

## Limitations

- This is a bounded native adaptation, not the paper's experimental score or an asymptotic guarantee.
- Public development generators can be inspected; independent generalization requires fresh instances after freezing the candidate.
