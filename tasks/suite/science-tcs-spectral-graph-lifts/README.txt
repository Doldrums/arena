# Theoretical computer science: Spectral graph-lift construction

**Source collection:** [Algorithms and theoretical computer science: source-based research tasks](../../papers/science-tcs_expansion.md)\
**Task id:** `science-tcs-spectral-graph-lifts`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

Spectral graph-lift construction under a bounded candidate interface with independent verification; generated mathematical instances, no external dataset.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

sign_edges(graph, budget) -> +/-1 edge signs. graph contains n and ordered undirected edges. Construct connected 3-regular two-lifts of prism graphs; minimize mean spectral radius of signed adjacency (the new eigenvalues), checked independently. budget=32 is the baseline trial budget; all candidates share the 60-second execution ceiling. Numerical spectral ranking does not certify a general theorem.

## Labels

Scientific contribution: `method` (tier 2); artifact `construction`, domain `mathematics`, data `synthetic`, verification `sampled`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `theoretical_computer_science`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **supported**.

Underlying problem: Choose graph-lift edge signs that keep new eigenvalues small and improve expansion.

Why it matters: Constructing graph lifts with strong spectral bounds is central to the cited Ramanujan-graph result.

- [Interlacing Families I: Bipartite Ramanujan Graphs of All Degrees](https://arxiv.org/abs/1304.4132): Main research objective: Establish infinite families of bipartite Ramanujan graphs through spectrally controlled graph lifts. Task connection: The local task searches signings of small prism graphs to minimize a spectral-radius objective. These finite constructions are a restricted instance of the signing problem; they do not prove the paper's infinite-family theorem.

The source directly studies the spectral construction target. Local finite-instance performance is not presented as a general graph-theoretic result.

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

- paper: https://annals.math.princeton.edu/2015/182-1/p07 (Interlacing families I: Bipartite Ramanujan graphs of all degrees: signed adjacency and eigenvalues of two-lifts.)

## Limitations

- This is a bounded native adaptation, not the paper's experimental score or an asymptotic guarantee.
- Public development generators can be inspected; independent generalization requires fresh instances after freezing the candidate.
