# LSR-Synth Materials

**Paper:** Deliberate Evolution: Agentic Reasoning for Sample-Efficient Symbolic Regression with LLMs (https://arxiv.org/pdf/2606.04360)\
**Task id:** `deliberate-evolution-lsr-synth-materials`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

LSR-Synth Materials

## Candidate interface

equation(X: np.ndarray[n, d], params: np.ndarray[10]) -> np.ndarray[n]; columns of X follow the instance's input_vars; parameters are fitted by BFGS on the train split. Score: mean NMSE on the test split over the selected LLM-SRBench instances

Parameters: `{"subset": "lsr_synth_matsci", "instance_id": null, "max_instances": 4, "seed": 0}`

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

- paper: https://arxiv.org/pdf/2606.04360 (Appendix E.1 Table 6 and real-world experiment)
- repository: https://github.com/Xinyu-Pang/Deliberate-Evolution/tree/18ae1f1c33a0dfa3c81298bba035036d3b23ecaf

## Limitations

- No root license was found in the inspected upstream tree; preserve upstream licensing conditions and do not assume redistribution rights.
- Paper states 240 problems in main text and 239 in Appendix E.1. Official repository contains only README.md at pinned commit.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
