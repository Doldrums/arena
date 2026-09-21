# E. coli growth

**Paper:** CoEvo: Continual Evolution of Symbolic Solutions Using Large Language Models (https://arxiv.org/pdf/2412.18890)\
**Paper:** DrSR: LLM based Scientific Equation Discovery with Dual Reasoning from Data and Experience (https://arxiv.org/pdf/2506.04282)\
**Task id:** `coevo-e-coli-growth`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

E. coli growth task evaluated in CoEvo: Continual Evolution of Symbolic Solutions Using Large Language Models.

Benchmark named in the paper: bactgrow. Paper metric: NMSE.

## Candidate interface

equation(<inputs>, params: np.ndarray[10]) -> np.ndarray prediction (LLM-SR contract); the ten parameters are fitted by BFGS on the training split. Score: NMSE on the in-distribution test split (OOD split also reported)

Parameters: `{"dataset": "bactgrow"}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `equation`, domain `natural_science`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate coevo-e-coli-growth --route upstream --paper <paper>`.

- DrSR: E. coli growth (`drsr-e-coli-growth`; E. coli growth)

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Benchmark data embedded from the MIT-licensed CoEvo release; the fitting loop follows the LLM-SR/CoEvo in-loop evaluator.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:scipy`

## Sources

- paper: https://arxiv.org/pdf/2412.18890 (Section 4, Table 1)
- repository: https://github.com/pgg3/CoEvo/tree/dcad65e9799961cf67cf29865ff41dda2902a808 (CoEvo/src/coevo/tasks/bactgrow.py)
- paper: https://arxiv.org/pdf/2506.04282 (Section 4.1 and Appendix B)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
