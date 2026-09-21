# Quantum information: fixed-depth QAOA parameter design

**Source collection:** [Quantum information: source-based research tasks](../../papers/science-quantum.md)\
**Task id:** `science-quantum-qaoa-maxcut`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Design graph-dependent two-layer QAOA angles maximizing the mean ratio of the independently simulated expected cut to the exact classical optimum on six small graphs. The circuit architecture is fixed; the candidate controls its parameter-selection algorithm.

Source-derived local benchmark; the exact objective and adaptations are specified below.

## Candidate interface

angles(n, edges, p) -> real array (p, 2), rows (gamma, beta) in radians. The fixed circuit starts in |+>^n and applies exp(-i gamma C), then exp(-i beta sum X), for each row; C is unweighted MaxCut. Return angles only. Six public evaluation graphs use n=6,8,10 and densities 0.25,0.55 (seed 713); use graph_cases(seed=113) for separate development graphs. Objective: mean expected-cut/exhaustive-optimum ratio. p=2; no shot noise or timing term.

Parameters: `{"layers": 2, "seed": 713}`

## Labels

Scientific contribution: `method` (tier 2); artifact `optimizer`, domain `natural_science`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

Research area: `quantum_information`.

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Optimize a two-layer QAOA circuit on six small MaxCut graph instances.

Why it matters: Qualifying evidence that this local task addresses a primary scientific problem has not been established.


The reviewed Farhi et al. paper (https://arxiv.org/abs/1411.4028) introduces a general quantum optimization algorithm and analyses MaxCut examples. It does not establish the local six-graph, fixed-depth parameter benchmark as a substantive primary scientific target under the stricter rule. A direct problem-focused justification remains to be established; this is not a claim that MaxCut or quantum optimization lacks scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Independent statevector reconstruction of Farhi et al. (2014), Eqs. (2)-(7), (11)-(12). Small locally generated graphs and p=2 are this suite's protocol, not the paper's experiments. The public evaluation graphs are not a secret test set; freeze candidates before evaluating new seeds for a generalization claim.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`

## Sources

- paper: https://arxiv.org/abs/1411.4028v1 (Farhi, Goldstone and Gutmann (2014), Sections I-II, Eqs. (2)-(7), (11)-(12): phase separator, mixer, expected cost and MaxCut Hamiltonian.)

## Limitations

- Independent ideal statevector reimplementation, not quantum hardware or a reproduction of the paper tables.
- Evaluation sizes, graph generator and two-layer budget are local choices. Small graphs can be solved classically; an improved score does not establish quantum advantage.
- Public deterministic validation graphs are separate from development seed 113, not hidden. Assess generalization only on fresh graphs after freezing the candidate.
