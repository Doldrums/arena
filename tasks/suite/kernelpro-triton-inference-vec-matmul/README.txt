# Triton inference vec_matmul

**Paper:** Optimizing CUDA like a Human: Micro-Profiling Tools as Expert Surrogates for LLM-Based GPU Kernel Optimization (https://arxiv.org/pdf/2606.26453)\
**Task id:** `kernelpro-triton-inference-vec-matmul`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Triton inference vec_matmul

## Candidate interface

One function per operator named in the task parameters (see README): each takes the operator's input tensors (float32, CPU) and returns the result tensor. Score: geometric mean over the operators of reference time / candidate time (best of 3 timed runs after a warm-up), higher is better; every output must match the PyTorch reference within the operator's tolerance.

Parameters: `{"ops": [{"name": "vec_matmul", "op": "vec_matmul", "params": {"m": 8192, "n": 8192, "vectors": 1}}], "seed": 0, "repeats": 3}`

## Labels

Scientific contribution: `engineering` (tier 3); artifact `kernel`, domain `systems`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- The Triton/CUDA kernel's operator and shapes are recreated on the CPU; energy-aware or GPU-specific objectives reduce to wall-clock speedup.
- CPU recreation of a GPU kernel task: the operator, shapes and correctness contract are kept; CUDA/Triton/NKI and the accelerator are replaced by float32 PyTorch on the CPU. The seed implements each operator with the plain PyTorch composition (speedup 1.0 by construction); speedups are comparable within the suite only.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:torch`

## Sources

- paper: https://arxiv.org/pdf/2606.26453 (Appendix C.3, Table 18)

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
