# GPUMODE TriMul A100

**Paper:** EurekAgent: Agent Environment Engineering is All You Need For Autonomous Scientific Discovery (https://arxiv.org/pdf/2606.13662)\
**Task id:** `eurekagent-gpumode-trimul-a100`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

GPUMODE TriMul A100

## Candidate interface

One function per operator named in the task parameters (see README): each takes the operator's input tensors (float32, CPU) and returns the result tensor. Score: geometric mean over the operators of reference time / candidate time (best of 3 timed runs after a warm-up), higher is better; every output must match the PyTorch reference within the operator's tolerance.

Parameters: `{"ops": [{"name": "trimul", "op": "trimul", "params": {"n": 256, "c": 128, "hidden": 128}}], "seed": 0, "repeats": 3}`

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

- paper: https://arxiv.org/pdf/2606.13662 (Sections 4.1–4.2)
- repository: https://github.com/THU-Team-Eureka/EurekAgent/tree/fb96df897dfb99797a77623aa0dd9ee178fe89d2 (examples/kernel_engineering_trimul_strict)

## Limitations

- Execution interface inspected in pinned source. Full paper experiments have not been reproduced here.
