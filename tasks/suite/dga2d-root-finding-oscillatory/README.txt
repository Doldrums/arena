# Root finding: Oscillatory

**Paper:** DGA2D: Directed Graph-Guided Automated Algorithm Design with Large Language Models (https://arxiv.org/pdf/2608.00700)\
**Paper:** A2DEPT: Large Language Model-Driven Automated Algorithm Design via Evolutionary Program Trees (https://arxiv.org/pdf/2604.24043)\
**Task id:** `dga2d-root-finding-oscillatory`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Root finding: Oscillatory

## Candidate interface

find_root(f, x0) -> x with |f(x)| <= 1e-8, at most 500 evaluations of f per problem. Score: success rate discounted by evaluations used

Parameters: `{"group": "oscillatory"}`

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `numerical_computing`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.

Underlying problem: Numerically solve the small synthetic equations in this local benchmark.

Why it matters: The current task is a generic numerical benchmark; a connection to a substantive scientific or real-world research objective has not been established by the supplied agent-framework citation.


Agent-framework evaluation and generic relevance of root-finding are insufficient under the primary-problem definition. A problem-focused paper and a substantive connection to this local task are required.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate dga2d-root-finding-oscillatory --route upstream --paper <paper>`.

- A2DEPT: Root finding: Oscillatory Functions (`a2dept-root-finding-oscillatory-functions`; 400 stochastic instances across four families)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/pdf/2608.00700 (Appendix G.3)
- paper: https://arxiv.org/pdf/2604.24043 (Appendix G.2, Table 18)

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- Paper says an anonymized implementation was supplied as supplementary material but no public URL was found in the extracted PDF.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
