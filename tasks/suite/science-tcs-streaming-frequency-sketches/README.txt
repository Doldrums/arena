# Theoretical computer science: Memory-bounded streaming frequency sketches

**Source collection:** [Algorithms and theoretical computer science: source-based research tasks](../../papers/science-tcs_expansion.md)\
**Task id:** `science-tcs-streaming-frequency-sketches`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Memory-bounded streaming frequency sketches under a bounded candidate interface with independent verification; generated mathematical instances, no external dataset.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

update(state: bytes, item: int) -> bytes; query(state: bytes, item: int) -> nonnegative frequency estimate. Initial state is1024 zero bytes; persistent state<=1024bytes. Fresh Python interpreter per256-item chunk, only state persists. Three1024-item insertion-only streams, universe400. Minimize mean absolute count error / stream length; top10recall diagnostic.15s perchunk,120s overall. Cooperative memory contract, not malicious-code sandbox.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `mathematics`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Estimate item frequencies accurately from a stream using sublinear, bounded memory.

Why it matters: Accuracy, space, and update costs for stream frequency summaries are the main algorithmic problems in the Count-Min paper.

- [An Improved Data Stream Summary: The Count-Min Sketch and its Applications](https://dsf.berkeley.edu/cs286/papers/countmin-latin2004.pdf): Main research objective: Provide efficient, space-limited approximations to point-frequency and related queries over data streams. Task connection: The local task estimates point frequencies under a fixed serialized-byte budget and an empirical error objective. Its workload and persistence boundary are local restrictions, not a proof of the paper's general probabilistic guarantees.

The cited paper directly solves bounded-memory streaming queries; the local score is an adaptation of that substantive algorithms problem.

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

- paper: https://www.cs.ox.ac.uk/people/graham.cormode/pubs/html/CormodeMuthukrishnan04CMJalg.html (Cormode and Muthukrishnan: Count-Min sketch, insertion-only frequency estimation.)
- paper: https://dimacs.rutgers.edu/~graham/pubs/papers/cm-full.pdf (Develops a memory-bounded sketch that estimates stream frequencies with provable error bounds. The local integer-stream and storage-budget protocol tests the same point-frequency estimation task.)

## Limitations

- This is a bounded native adaptation, not the paper's experimental score or an asymptotic guarantee.
- Public development generators can be inspected; independent generalization requires fresh instances after freezing the candidate.
- Memory persistence is constrained through fresh subprocesses and a bytes interface; this is not an OS sandbox for malicious candidates.
