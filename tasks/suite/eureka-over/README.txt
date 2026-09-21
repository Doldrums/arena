# Over

**Paper:** Eureka: Human-Level Reward Design via Coding Large Language Models (https://arxiv.org/pdf/2310.12931)\
**Task id:** `eureka-over`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Over: optimize the candidate specified by the paper and evaluate against the named benchmark.

Benchmark named in the paper: Bi-DexHands. Paper metric: task-specific fitness and human-normalized score.

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `reward`, domain `robotics`, data `simulator`, verification `none`, reference `none`, resources `simulator`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness requires a physics simulator or reinforcement-learning training loop (Bi-DexHands) that is not bundled.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `environment:Bi-DexHands`

## Sources

- paper: https://arxiv.org/pdf/2310.12931 (Appendix B task table)
- repository: https://github.com/eureka-research/Eureka/tree/9eee42808b52d8abc14845d1547bfde886403ccc (eureka/cfg/env/shadow_hand_over.yaml)

## Limitations

- Upstream commands and dependencies were inspected; costly training, paid APIs, and hardware experiments were not executed.
- Pinned cfg/config.yaml selects historical model gpt-4-0314 and the legacy OpenAI SDK. Configure a compatible available endpoint/model before execution; changing models changes reproduction conditions.
- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
