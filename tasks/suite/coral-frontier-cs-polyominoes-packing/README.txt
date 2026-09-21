# Frontier-CS Polyominoes packing

**Paper:** CORAL: Towards Autonomous Multi-Agent Evolution for Open-Ended Discovery (https://arxiv.org/pdf/2604.01658)\
**Task id:** `coral-frontier-cs-polyominoes-packing`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Frontier-CS Polyominoes packing

Benchmark named in the paper: Frontier-CS. Paper metric: packing score.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `public_benchmark`, verification `none`, reference `none`, resources `docker, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Frontier-CS problems are judged by the Frontier-CS evaluation service (Docker judge and hidden tests), which is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `toolchain:Frontier-CS judge`
- `docker`

## Sources

- paper: https://arxiv.org/pdf/2604.01658 (Section 4.1 stress tests)
- repository: https://github.com/Human-Agent-Society/CORAL/tree/0123dfb939b35228cf2c1fde224cd0561e727408 (examples/frontier_cs_algo/0)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
