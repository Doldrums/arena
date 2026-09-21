# LSR-Synth CRK0

**Paper:** DrSR: LLM based Scientific Equation Discovery with Dual Reasoning from Data and Experience (https://arxiv.org/pdf/2506.04282)\
**Task id:** `drsr-lsr-synth-crk0`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

LSR-Synth CRK0 task evaluated in DrSR: LLM based Scientific Equation Discovery with Dual Reasoning from Data and Experience.

Benchmark named in the paper: LSR-Synth CRK0. Paper metric: normalized mean squared error.

## Candidate interface

equation(X: np.ndarray[n, d], params: np.ndarray[10]) -> np.ndarray[n]; columns of X follow the instance's input_vars; parameters are fitted by BFGS on the train split. Score: mean NMSE on the test split over the selected LLM-SRBench instances

Parameters: `{"subset": "lsr_synth_chem_react", "instance_id": "crk0", "max_instances": 4, "seed": 0}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `equation`, domain `natural_science`, data `synthetic`, verification `exact`, reference `none`, resources `network`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Data from the public LLM-SRBench mirror pkuHaowei/llm-srbench; the fitting loop follows the LLM-SR evaluator. Whole-subset tasks use a seeded sample of four instances.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:datasets`
- `network:huggingface pkuHaowei/llm-srbench`
- `py:scipy`

## Sources

- paper: https://arxiv.org/pdf/2506.04282 (Section 4.1 and Appendix B)
- repository: https://github.com/pgg3/CoEvo/tree/dcad65e9799961cf67cf29865ff41dda2902a808

## Limitations

- arXiv HTML unavailable; full PDF retrieved and text extracted.
- No official public runnable implementation verified from the inspected paper. External benchmark code may exist separately.
- pgg3/CoEvo is pinned only as the paper-cited LLM-SR benchmark source; DrSR's own code has not been released.
- LSR-Transform and LSR-Synth evaluation needs the LLM-SRBench package and its datasets, which are not pinned here; DrSR itself has no public implementation.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
