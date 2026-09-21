# KAN gravitational potential x*y/z

**Paper:** Symbolic Regression with Multimodal Large Language Models and Kolmogorov–Arnold Networks (https://arxiv.org/pdf/2505.07956)\
**Task id:** `llm-lex-kan-gravitational-potential-x-y-z`\
**Protocol:** `recreated`\
**Direction:** minimize\

## Task

KAN gravitational potential x*y/z task evaluated in Symbolic Regression with Multimodal Large Language Models and Kolmogorov–Arnold Networks.

Benchmark named in the paper: KAN gravitational potential x*y/z. Paper metric: scale-normalized squared fitting error (Equation 3).

## Candidate interface

equation(<inputs>, params: np.ndarray[10]) -> np.ndarray prediction; parameters fitted by BFGS on generated training data. Score: NMSE on generated test data

Parameters: `{"target": "kan_gravitational", "seed": 0}`

## Labels

Scientific contribution: `rediscovery` (tier 2); artifact `equation`, domain `natural_science`, data `synthetic`, verification `exact`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

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

- paper: https://arxiv.org/pdf/2505.07956 (Section 3.2 Example 3)
- repository: https://github.com/harveyThomas4692/llmlex/tree/9f02b58c5efb6d3c973c2ad2552ecc3a57998f81 (Examples/Example Paper MultiKAN.ipynb)

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
