# Easy pickup

**Paper:** Discovering Reinforcement Learning Interfaces with Large Language Models (https://arxiv.org/pdf/2605.03408)\
**Task id:** `limen-easy-pickup`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Pick up blue pyramid in 9x9 grid; 80-step horizon

Benchmark named in the paper: XLand-MiniGrid. Paper metric: mean success rate across three seeds.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `reward`, domain `robotics`, data `simulator`, verification `none`, reference `none`, resources `simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires a physics simulator or reinforcement-learning training loop (XLand-MiniGrid) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `environment:XLand-MiniGrid`

## Sources

- paper: https://arxiv.org/pdf/2605.03408 (Section 5.1)
- repository: https://github.com/Lossfunk/LIMEN/tree/cf0b44da37f7e7ee038920c860a8cb00c610c9af (configs/easy_pickup.yaml)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
