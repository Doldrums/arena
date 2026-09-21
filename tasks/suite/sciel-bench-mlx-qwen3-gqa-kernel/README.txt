# SCiEL: MLX Metal GQA attention kernel for Qwen3-0.6B

**Paper:** SCiEL — Scientific Closed-loop Evolutionary Learning: benchmark examples (https://github.com/luciferkonn/SCiEL)\
**Task id:** `sciel-bench-mlx-qwen3-gqa-kernel`\
**Protocol:** `original`\
**Direction:** maximize\

## Task

Evolve a custom Metal kernel (CustomGQAAttention) for grouped-query attention in Qwen3-0.6B-bf16 on Apple Silicon. The pinned evaluator validates the kernel, checks bfloat16 correctness against MLX's scaled_dot_product_attention and benchmarks decode/prefill throughput through mlx_lm.generate in a subprocess hook; final_score is a safety-adjusted performance score.

Benchmark named in the paper: SCiEL source example mlx_metal_kernel_opt. Paper metric: final_score.

## Candidate interface

See evaluator.py and README.upstream.md.

## Labels

Scientific contribution: `engineering` (tier 3); artifact `kernel`, domain `systems`, data `public_benchmark`, verification `simulation`, reference `none`, resources `network`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Verbatim copy of the pinned SCiEL example `examples/mlx_metal_kernel_opt` (commit da80706f98f9); the evaluator, seed program and configuration are the upstream files. README.upstream.md is the upstream README when one exists.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `network:huggingface mlx-community/Qwen3-0.6B-bf16`
- `platform:darwin-arm64`
- `py:mlx`
- `py:mlx_lm`
- `py:numpy`
- `py:psutil`
- `py:scipy`
- `py:yaml`

## Sources

- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/mlx_metal_kernel_opt/evaluator.py (evaluate and helper functions at immutable commit)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/mlx_metal_kernel_opt/initial_program.py (original baseline)
- repository: https://github.com/luciferkonn/SCiEL/blob/da80706f98f9bf1295e502544cdf5a9200fe5f57/examples/mlx_metal_kernel_opt/README.md (source README)

## Limitations

- Source-inspected SCiEL example; not a reproduced paper result.
- The original evaluator and baseline are fetched at the immutable source commit; no upstream implementation is silently repaired.
- Hardware-specific: results depend on the Apple GPU generation, MLX version and thermal state; the source README reports the best evolved kernel was slower than the MLX baseline.
