# Qwen3-1.7B end-to-end SGLang kernel optimization

**Paper:** Agentic Optimization: A Framework for Autonomous Coding-Agent Search (https://junye-pan.github.io/posts/agentic-optimization/assets/report.pdf)\
**Task id:** `agentic-optimization-qwen3-1-7b-end-to-end-sglang-kernel-optimization`\
**Protocol:** `unsupported`\
**Direction:** maximize\

## Task

Qwen3-1.7B end-to-end SGLang kernel optimization

## Candidate interface

See the docstring in `evaluator.py`.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `kernel`, domain `systems`, data `synthetic`, verification `none`, reference `none`, resources `gpu, unavailable`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Not executable in this suite: Fitness is accelerator wall-clock or model training on GPU hardware (Qwen3-1.7B end-to-end SGLang kernel optimization); it cannot be measured on a CPU-only suite.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `hardware:gpu`
- `dataset:Qwen3-1.7B end-to-end SGLang kernel optimization`

## Sources

- paper: https://junye-pan.github.io/posts/agentic-optimization/assets/report.pdf (Report Section 5.2)
- repository: https://github.com/Junye-Pan/AgenticOptimization/tree/712b2fd4888c4b57fc08c1d2bdf4b1ca4c4517fb (tasks/llm_inference_qwen3_1_7b_sglang_4090)

## Limitations

- No root license or dependency manifest found in inspected repository; README mentions design.md but file is absent at pinned commit.
- Requires an NVIDIA RTX 4090 with SGLang/CUDA kernels; the pinned task packages contain server-side evaluators for that hardware only.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
