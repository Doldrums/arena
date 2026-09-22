# GQA 32 query heads 4 KV heads, non-causal, sequence 16384

**Paper:** AVO: Agentic Variation Operators for Autonomous Evolutionary Search (https://arxiv.org/pdf/2603.24517)\
**Task id:** `avo-gqa-32-query-heads-4-kv-heads-non-causal-sequence-16384`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

BF16 forward-prefill attention, head dimension 128, batch size 2, fixed 32768 total tokens.

Benchmark named in the paper: FlashAttention-4 timing protocol. Paper metric: TFLOPS.

## Candidate interface

attention(q, k, v, causal) -> torch.Tensor of shape (batch, heads_q, seq, dim): scaled dot-product attention in float32 on the CPU; k and v have heads_kv heads (grouped-query attention repeats each kv head for heads_q // heads_kv query heads); causal masks future positions. Score: achieved TFLOPS of the candidate (4*B*Hq*S*S*D flops, halved when causal) at the task's shapes, best of 3 timed runs after a warm-up; the output must match torch's scaled_dot_product_attention within 1e-3 relative error.

Parameters: `{"ops": [{"name": "attention", "op": "attention", "params": {"batch": 2, "heads_q": 32, "heads_kv": 4, "seq": 16384, "dim": 128, "causal": false}}], "seed": 0, "repeats": 3}`

## Labels

Scientific contribution: `engineering` (tier 3); artifact `kernel`, domain `systems`, data `synthetic`, verification `simulation`, reference `none`, resources `cpu`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- AVO benchmark configuration kept exactly (head dim 128, 2 x 16384 = 32768 tokens); BF16 on B200 replaced by float32 on the CPU.
- CPU recreation of the paper's attention-kernel task at the paper's shapes: the accelerator and BF16 kernels are replaced by float32 PyTorch on the CPU, and the reference is torch.nn.functional.scaled_dot_product_attention. TFLOPS are comparable within the suite only.

## CPU timing revision

CPU timing revision arena.kernel-cpu.single-thread/1: one PyTorch intra-op and one inter-op thread, with OMP/MKL/OpenBLAS/NumExpr thread limits set to 1. Shapes, float32 correctness tolerances, warm-up, repeats and score formulas are unchanged. Historical host-wide-thread timings are retained as historical evidence and are not comparable to this revision. Fresh seed timing and memory preflight is still required; a CPU recreation is not a GPU-paper reproduction.

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `py:torch`

## Sources

- paper: https://arxiv.org/pdf/2603.24517 (Section 4.1 Benchmark Configurations)

## Limitations

- No official implementation repository link identified in the inspected source. Paper specification is recorded; runnable reproduction is not verified.
- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
- No publicly accessible, paper-linked implementation with a verified immutable revision was established.
