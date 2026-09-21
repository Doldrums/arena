# Theoretical computer science: Communication-minimizing DAG pebbling

**Source collection:** [Algorithms and theoretical computer science: source-based research tasks](../../papers/science-tcs_expansion.md)\
**Task id:** `science-tcs-red-blue-pebbling`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Communication-minimizing DAG pebbling under a bounded candidate interface with independent verification; generated mathematical instances, no external dataset.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

pebble(dag, fast_memory_budget) -> list of [operation, vertex], with operations load/store/compute/delete. dag has topologically ordered parents and output vertices. Inputs start blue, all outputs must finish blue; every red value consumes one fast-memory slot, including newly computed results. Recomputations allowed; at most20000 operations. Score mean transfers / naive schedule on three layered DAGs; exact state-machine verification.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `mathematics`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Minimize data movement when evaluating a dependency graph with limited fast memory.

Why it matters: Communication cost under memory constraints is the explicit computational-complexity problem introduced by the source.

- [I/O Complexity: The Red-Blue Pebble Game](https://www.eecs.harvard.edu/~htk/publication/1981-stoc-hong-kung.pdf): Main research objective: Characterize and bound the input/output cost of computations with limited fast memory using pebble games. Task connection: The local task constructs legal bounded-memory schedules for finite DAGs and counts loads and stores. Its instance family and verifier rules are a restricted scheduling adaptation and do not reproduce asymptotic bounds for matrix multiplication or FFT.

The scientific target is communication-efficient computation itself, rather than incidental scoring of a planning agent.

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

- paper: https://www.eecs.harvard.edu/~htk/publication/1981-stoc-hong-kung.pdf (Hong and Kung: red-blue pebble game, dependency and transfer rules.)

## Limitations

- This is a bounded native adaptation, not the paper's experimental score or an asymptotic guarantee.
- Public development generators can be inspected; independent generalization requires fresh instances after freezing the candidate.
