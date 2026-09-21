# Frontier-CS

**Paper:** EvoX: Meta-Evolution for Automated Discovery (https://arxiv.org/pdf/2602.23413)\
**Paper:** AdaEvolve: Adaptive LLM Driven Zeroth-Order Optimization (https://arxiv.org/pdf/2602.20133)\
**Task id:** `evox-frontier-cs`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Frontier-CS

Benchmark named in the paper: Frontier-CS. Paper metric: official benchmark score.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `method` (tier 2); artifact `program`, domain `combinatorial_optimisation`, data `public_benchmark`, verification `none`, reference `none`, resources `docker, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Also evaluated by

The same problem (same evaluator and parameters) appears in these papers; their records were merged into this task and their pinned upstream routes remain reachable with `run.py evaluate evox-frontier-cs --route upstream --paper <paper>`.

- AdaEvolve: Frontier-CS (`adaevolve-frontier-cs`; Frontier-CS, 172 problems)

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

- paper: https://arxiv.org/pdf/2602.23413 (Experimental evaluation and additional-results appendix)
- repository: https://github.com/skydiscover-ai/skydiscover/tree/0d932b690670a7e544388ad362e9876c8bd256a0 (benchmarks/frontier-cs-eval)
- paper: https://arxiv.org/pdf/2602.20133 (Experimental evaluation and additional-results appendix)

## Limitations

- Appendix task prose conflicts with standard circle-packing/Heilbronn definitions; the pinned evaluator is authoritative. Telemetry-repair directory is not present at inspected commit.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
