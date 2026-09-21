"""CPU recreations of GPU kernel-optimisation tasks (AVO, KernelPro, AccelOpt, EurekAgent TriMul, Agentic Optimization).

The papers evolve CUDA, Triton or NKI kernels and score wall-clock throughput
on accelerators. This module keeps the *problem* (the operator, its shapes and
the correctness contract) and replaces the hardware with the CPU: a candidate
implements the operator with PyTorch tensor operations (or NumPy) and is scored
by measured throughput against a PyTorch reference, after an exact correctness
check. Scores are comparable within the suite, not with the papers' TFLOPS.

Every operator is a ``Spec`` with an input generator, a reference
implementation, a FLOP count and tolerances. Timings take the best of several
repeats after a warm-up; all threads of the machine are used.
"""
from __future__ import annotations

import math
import os
import time

import numpy as np

from .runtime import CandidateError, require

try:
    import torch
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - reported as a requirement by the harness
    torch = None
    F = None


def _torch():
    if torch is None:
        raise CandidateError("torch is required for the CPU kernel tasks (pip install torch)")
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    return torch


def _gen(seed):
    return torch.Generator().manual_seed(seed)


def _randn(shape, gen, scale=1.0):
    return torch.randn(*shape, generator=gen, dtype=torch.float32) * scale


# ---------------------------------------------------------------------------
# operator library: name -> (make_inputs(seed, params), reference(*inputs), flops(params), (rtol, atol))
# ---------------------------------------------------------------------------

def _attention_inputs(seed, p):
    g = _gen(seed)
    b, hq, hkv, s, d = p["batch"], p["heads_q"], p["heads_kv"], p["seq"], p.get("dim", 128)
    return (_randn((b, hq, s, d), g), _randn((b, hkv, s, d), g), _randn((b, hkv, s, d), g), bool(p["causal"]))


def _attention_reference(q, k, v, causal):
    if k.shape[1] != q.shape[1]:
        rep = q.shape[1] // k.shape[1]
        k = k.repeat_interleave(rep, dim=1)
        v = v.repeat_interleave(rep, dim=1)
    return F.scaled_dot_product_attention(q, k, v, is_causal=causal)


def _attention_flops(p):
    b, hq, s, d = p["batch"], p["heads_q"], p["seq"], p.get("dim", 128)
    return 4.0 * b * hq * s * s * d * (0.5 if p["causal"] else 1.0)


def _decode_attention_inputs(seed, p):
    g = _gen(seed)
    b, h, d, kv = p.get("batch", 32), p.get("heads", 32), p.get("dim", 128), p.get("kv_len", 2048)
    return (_randn((b, h, 1, d), g), _randn((b, h, kv, d), g), _randn((b, h, kv, d), g))


def _paged_attention_inputs(seed, p):
    g = _gen(seed)
    b, h, d, page, max_len = p.get("batch", 8), p.get("heads", 32), p.get("dim", 128), p.get("page", 16), p.get("kv_len", 1024)
    blocks_per_seq = max_len // page
    lengths = torch.randint(page, max_len + 1, (b,), generator=g)
    k_cache = _randn((b * blocks_per_seq, page, h, d), g)
    v_cache = _randn((b * blocks_per_seq, page, h, d), g)
    tables = torch.arange(b * blocks_per_seq).reshape(b, blocks_per_seq)
    return (_randn((b, h, d), g), k_cache, v_cache, tables, lengths)


def _paged_attention_reference(q, k_cache, v_cache, tables, lengths):
    outputs = []
    page = k_cache.shape[1]
    for i in range(q.shape[0]):
        n = int(lengths[i])
        blocks = tables[i, : math.ceil(n / page)]
        k = k_cache[blocks].reshape(-1, k_cache.shape[2], k_cache.shape[3])[:n]  # (n, h, d)
        v = v_cache[blocks].reshape(-1, v_cache.shape[2], v_cache.shape[3])[:n]
        scores = torch.einsum("hd,nhd->hn", q[i], k) / math.sqrt(q.shape[-1])
        outputs.append(torch.einsum("hn,nhd->hd", torch.softmax(scores, dim=-1), v))
    return torch.stack(outputs)


def _matmul_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["m"], p["k"]), g, 1 / math.sqrt(p["k"])), _randn((p["k"], p["n"]), g, 1 / math.sqrt(p["k"])))


def _bmm_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["b"], p["m"], p["k"]), g, 1 / math.sqrt(p["k"])), _randn((p["b"], p["k"], p["n"]), g, 1 / math.sqrt(p["k"])))


def _layernorm_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["m"], p["n"]), g), 1 + 0.1 * _randn((p["n"],), g), 0.1 * _randn((p["n"],), g))


def _rmsnorm(x, w, eps=1e-6):
    return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + eps) * w


def _conv_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p.get("b", 8), p["cin"], p["hw"], p["hw"]), g), _randn((p["cout"], p["cin"], 3, 3), g, 1 / math.sqrt(9 * p["cin"])))


def _conv_bn_relu_inputs(seed, p):
    x, w = _conv_inputs(seed, p)
    g = _gen(seed + 1)
    c = p["cout"]
    return (x, w, 1 + 0.1 * _randn((c,), g), 0.1 * _randn((c,), g), 0.1 * _randn((c,), g), 1 + 0.5 * torch.rand(c, generator=g))


def _conv_bn_relu_reference(x, w, gamma, beta, mean, var):
    y = F.conv2d(x, w, padding=1)
    y = (y - mean[None, :, None, None]) / torch.sqrt(var[None, :, None, None] + 1e-5) * gamma[None, :, None, None] + beta[None, :, None, None]
    return torch.relu(y)


def _mlp_inputs(seed, p):
    g = _gen(seed)
    t, d, f = p["tokens"], p["d"], p["ff"]
    return (_randn((t, d), g), _randn((d, f), g, 1 / math.sqrt(d)), 0.1 * _randn((f,), g), _randn((f, d), g, 1 / math.sqrt(f)), 0.1 * _randn((d,), g))


def _mlp_reference(x, w1, b1, w2, b2):
    return F.gelu(x @ w1 + b1) @ w2 + b2


def _transformer_inputs(seed, p):
    g = _gen(seed)
    t, d, f = p["tokens"], p["d"], p["ff"]
    return (_randn((1, t, d), g), _randn((d, 3 * d), g, 1 / math.sqrt(d)), _randn((d, d), g, 1 / math.sqrt(d)), 1 + 0.1 * _randn((d,), g), 0.1 * _randn((d,), g),
            _randn((d, f), g, 1 / math.sqrt(d)), 0.1 * _randn((f,), g), _randn((f, d), g, 1 / math.sqrt(f)), 0.1 * _randn((d,), g), int(p["heads"]))


def _transformer_reference(x, wqkv, wo, ln_w, ln_b, w1, b1, w2, b2, heads):
    b, t, d = x.shape
    h = F.layer_norm(x, (d,), ln_w, ln_b)
    q, k, v = (h @ wqkv).split(d, dim=-1)
    q, k, v = (z.reshape(b, t, heads, d // heads).transpose(1, 2) for z in (q, k, v))
    a = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(b, t, d) @ wo
    x = x + a
    h = F.layer_norm(x, (d,), ln_w, ln_b)
    return x + F.gelu(h @ w1 + b1) @ w2 + b2


def _moe_inputs(seed, p):
    g = _gen(seed)
    t, d, e, f = p["tokens"], p["d"], p["experts"], p["ff"]
    return (_randn((t, d), g), _randn((d, e), g, 1 / math.sqrt(d)), _randn((e, d, f), g, 1 / math.sqrt(d)), _randn((e, f, d), g, 1 / math.sqrt(f)), int(p.get("top_k", 2)))


def _moe_reference(x, gate_w, w1, w2, top_k):
    logits = x @ gate_w
    weights, experts = torch.topk(torch.softmax(logits, dim=-1), top_k, dim=-1)
    weights = weights / weights.sum(-1, keepdim=True)
    out = torch.zeros_like(x)
    for e in range(w1.shape[0]):
        for slot in range(top_k):
            rows = (experts[:, slot] == e).nonzero(as_tuple=True)[0]
            if rows.numel():
                out[rows] += weights[rows, slot, None] * (F.silu(x[rows] @ w1[e]) @ w2[e])
    return out


def _grouped_gemm_inputs(seed, p):
    g = _gen(seed)
    t, k, n, groups = p["tokens"], p["k"], p["n"], p["groups"]
    cuts = torch.sort(torch.randint(1, t, (groups - 1,), generator=g)).values
    sizes = torch.diff(torch.cat([torch.tensor([0]), cuts, torch.tensor([t])]))
    return (_randn((t, k), g), _randn((t, n), g), sizes)


def _grouped_gemm_reference(x, dy, sizes):
    out, start = [], 0
    for size in sizes.tolist():
        out.append(x[start:start + size].T @ dy[start:start + size])
        start += size
    return torch.stack(out)


def _adamw_inputs(seed, p):
    g = _gen(seed)
    shape = (p["m"], p["n"])
    return (_randn(shape, g), _randn(shape, g, 0.01), _randn(shape, g, 0.01), torch.rand(*shape, generator=g) * 1e-4, 3, 1e-3, 0.9, 0.999, 1e-8, 0.01)


def _adamw_reference(param, grad, m, v, step, lr, beta1, beta2, eps, wd):
    m2 = beta1 * m + (1 - beta1) * grad
    v2 = beta2 * v + (1 - beta2) * grad * grad
    m_hat = m2 / (1 - beta1 ** step)
    v_hat = v2 / (1 - beta2 ** step)
    return torch.stack([param * (1 - lr * wd) - lr * m_hat / (torch.sqrt(v_hat) + eps), m2, v2])


def _rope_inputs(seed, p):
    g = _gen(seed)
    b, h, n, d = p.get("b", 1), p["heads"], p["seq"], p["dim"]
    pos = torch.arange(n, dtype=torch.float32)[:, None]
    inv = 1.0 / (10000 ** (torch.arange(0, d, 2, dtype=torch.float32) / d))
    ang = pos * inv[None, :]
    return (_randn((b, h, n, d), g), torch.cos(ang), torch.sin(ang))


def _rope_reference(x, cos, sin):
    x1, x2 = x[..., 0::2], x[..., 1::2]
    out = torch.empty_like(x)
    out[..., 0::2] = x1 * cos - x2 * sin
    out[..., 1::2] = x1 * sin + x2 * cos
    return out


def _mamba_inputs(seed, p):
    g = _gen(seed)
    length, channels, state = p["seq"], p["channels"], p["state"]
    return (_randn((length, channels), g), torch.nn.functional.softplus(_randn((length, channels), g)) * 0.1, -torch.rand(channels, state, generator=g) - 0.5,
            _randn((length, state), g, 0.3), _randn((length, state), g, 0.3), _randn((channels,), g, 0.1))


def _mamba_reference(u, delta, A, B, C, D):
    h = torch.zeros(u.shape[1], A.shape[1])
    ys = []
    for t in range(u.shape[0]):
        dA = torch.exp(delta[t][:, None] * A)
        dB = delta[t][:, None] * B[t][None, :]
        h = dA * h + dB * u[t][:, None]
        ys.append(h @ C[t] + D * u[t])
    return torch.stack(ys)


def _trimul_inputs(seed, p):
    g = _gen(seed)
    n, c, hidden = p["n"], p["c"], p["hidden"]
    x = _randn((1, n, n, c), g)
    mask = (torch.rand(1, n, n, generator=g) > 0.1).float()
    return (x, mask, 1 + 0.1 * _randn((c,), g), 0.1 * _randn((c,), g), _randn((c, hidden), g, 1 / math.sqrt(c)), _randn((c, hidden), g, 1 / math.sqrt(c)),
            _randn((c, hidden), g, 1 / math.sqrt(c)), _randn((c, hidden), g, 1 / math.sqrt(c)), 1 + 0.1 * _randn((hidden,), g), 0.1 * _randn((hidden,), g),
            _randn((c, c), g, 1 / math.sqrt(c)), _randn((hidden, c), g, 1 / math.sqrt(hidden)))


def _trimul_reference(x, mask, ln_w, ln_b, w_left, w_left_gate, w_right, w_right_gate, ln2_w, ln2_b, w_gate, w_out):
    h = F.layer_norm(x, (x.shape[-1],), ln_w, ln_b)
    m = mask[..., None]
    left = torch.sigmoid(h @ w_left_gate) * (h @ w_left) * m
    right = torch.sigmoid(h @ w_right_gate) * (h @ w_right) * m
    prod = torch.einsum("bikc,bjkc->bijc", left, right)
    prod = F.layer_norm(prod, (prod.shape[-1],), ln2_w, ln2_b)
    return torch.sigmoid(h @ w_gate) * (prod @ w_out)


def _softmax_inputs(seed, p):
    return (_randn((p["m"], p["n"]), _gen(seed)),)


def _act_inputs(seed, p):
    return (_randn((p["m"], p["n"]), _gen(seed)),)


def _bias_relu_inputs(seed, p):
    a, b = _matmul_inputs(seed, p)
    return (a, b, 0.1 * _randn((p["n"],), _gen(seed + 1)))


def _matmul_ln_inputs(seed, p):
    a, b = _matmul_inputs(seed, p)
    g = _gen(seed + 1)
    return (a, b, 1 + 0.1 * _randn((p["n"],), g), 0.1 * _randn((p["n"],), g))


def _add_rmsnorm_matmul_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["m"], p["k"]), g), _randn((p["m"], p["k"]), g), 1 + 0.1 * _randn((p["k"],), g), _randn((p["k"], p["n"]), g, 1 / math.sqrt(p["k"])))


def _rmsnorm_matmul_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["m"], p["k"]), g), 1 + 0.1 * _randn((p["k"],), g), _randn((p["k"], p["n"]), g, 1 / math.sqrt(p["k"])))


def _matmul_add_rmsnorm_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["m"], p["k"]), g), _randn((p["k"], p["n"]), g, 1 / math.sqrt(p["k"])), _randn((p["m"], p["n"]), g), 1 + 0.1 * _randn((p["n"],), g))


def _lora_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["m"], p["k"]), g), _randn((p["k"], p["n"]), g, 1 / math.sqrt(p["k"])), _randn((p["k"], p["r"]), g, 1 / math.sqrt(p["k"])), _randn((p["r"], p["n"]), g, 1 / math.sqrt(p["r"])))


def _swiglu_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["m"], p["k"]), g), _randn((p["k"], p["n"]), g, 1 / math.sqrt(p["k"])), _randn((p["k"], p["n"]), g, 1 / math.sqrt(p["k"])))


def _transpose_matmul_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["k"], p["m"]), g, 1 / math.sqrt(p["k"])), _randn((p["k"], p["n"]), g, 1 / math.sqrt(p["k"])))


def _vec_matmul_inputs(seed, p):
    g = _gen(seed)
    return (_randn((p["m"], p["n"]), g, 1 / math.sqrt(p["n"])), _randn((p["n"], p.get("vectors", 1)), g))


def _mm_flops(p):
    return 2.0 * p["m"] * p["k"] * p["n"]


OPS = {
    "attention": (_attention_inputs, _attention_reference, _attention_flops, (1e-3, 2e-3)),
    "decode_attention": (_decode_attention_inputs, lambda q, k, v: F.scaled_dot_product_attention(q, k, v), lambda p: 4.0 * p.get("batch", 32) * p.get("heads", 32) * p.get("kv_len", 2048) * p.get("dim", 128), (1e-3, 2e-3)),
    "paged_attention": (_paged_attention_inputs, _paged_attention_reference, lambda p: 4.0 * p.get("batch", 8) * p.get("heads", 32) * p.get("kv_len", 1024) * p.get("dim", 128), (1e-3, 2e-3)),
    "matmul": (_matmul_inputs, lambda a, b: a @ b, _mm_flops, (1e-4, 1e-4)),
    "gemm_split_k": (_matmul_inputs, lambda a, b: a @ b, _mm_flops, (1e-4, 1e-4)),
    "transpose_matmul": (_transpose_matmul_inputs, lambda a, b: a.T @ b, _mm_flops, (1e-4, 1e-4)),
    "bmm": (_bmm_inputs, lambda a, b: torch.bmm(a, b), lambda p: 2.0 * p["b"] * p["m"] * p["k"] * p["n"], (1e-4, 1e-4)),
    "bmm_softmax": (_bmm_inputs, lambda a, b: torch.softmax(torch.bmm(a, b), dim=-1), lambda p: 2.0 * p["b"] * p["m"] * p["k"] * p["n"] + 5.0 * p["b"] * p["m"] * p["n"], (1e-4, 1e-5)),
    "vec_matmul": (_vec_matmul_inputs, lambda a, x: a @ x, lambda p: 2.0 * p["m"] * p["n"] * p.get("vectors", 1), (1e-4, 1e-4)),
    "persistent_vec_matmul": (_vec_matmul_inputs, lambda a, x: a @ x, lambda p: 2.0 * p["m"] * p["n"] * p.get("vectors", 1), (1e-4, 1e-4)),
    "softmax": (_softmax_inputs, lambda x: torch.softmax(x, dim=-1), lambda p: 5.0 * p["m"] * p["n"], (1e-5, 1e-6)),
    "relu": (_act_inputs, torch.relu, lambda p: 1.0 * p["m"] * p["n"], (0.0, 0.0)),
    "silu": (_act_inputs, F.silu, lambda p: 4.0 * p["m"] * p["n"], (1e-5, 1e-6)),
    "swish": (_act_inputs, F.silu, lambda p: 4.0 * p["m"] * p["n"], (1e-5, 1e-6)),
    "layer_norm": (_layernorm_inputs, lambda x, w, b: F.layer_norm(x, (x.shape[-1],), w, b), lambda p: 8.0 * p["m"] * p["n"], (1e-4, 1e-4)),
    "rmsnorm": (_layernorm_inputs, lambda x, w, b: _rmsnorm(x, w), lambda p: 4.0 * p["m"] * p["n"], (1e-4, 1e-4)),
    "conv2d": (_conv_inputs, lambda x, w: F.conv2d(x, w, padding=1), lambda p: 2.0 * p.get("b", 8) * p["cout"] * p["cin"] * 9 * p["hw"] * p["hw"], (1e-4, 1e-4)),
    "gemm_bias_relu": (_bias_relu_inputs, lambda a, b, bias: torch.relu(a @ b + bias), _mm_flops, (1e-4, 1e-4)),
    "conv_bn_relu": (_conv_bn_relu_inputs, _conv_bn_relu_reference, lambda p: 2.0 * p.get("b", 8) * p["cout"] * p["cin"] * 9 * p["hw"] * p["hw"], (1e-4, 1e-4)),
    "matmul_layer_norm": (_matmul_ln_inputs, lambda a, b, w, bias: F.layer_norm(a @ b, (b.shape[1],), w, bias), _mm_flops, (1e-4, 1e-4)),
    "mlp_block": (_mlp_inputs, _mlp_reference, lambda p: 4.0 * p["tokens"] * p["d"] * p["ff"], (1e-4, 1e-4)),
    "transformer_block": (_transformer_inputs, _transformer_reference, lambda p: 2.0 * p["tokens"] * p["d"] * (4 * p["d"] + 2 * p["ff"]) + 2.0 * p["tokens"] * p["tokens"] * p["d"], (1e-3, 1e-3)),
    "fused_moe": (_moe_inputs, _moe_reference, lambda p: 4.0 * p["tokens"] * p.get("top_k", 2) * p["d"] * p["ff"], (1e-4, 1e-4)),
    "grouped_gemm_weight_gradient": (_grouped_gemm_inputs, _grouped_gemm_reference, lambda p: 2.0 * p["tokens"] * p["k"] * p["n"], (1e-4, 1e-4)),
    "adamw": (_adamw_inputs, _adamw_reference, lambda p: 12.0 * p["m"] * p["n"], (1e-5, 1e-6)),
    "rope": (_rope_inputs, _rope_reference, lambda p: 6.0 * p.get("b", 1) * p["heads"] * p["seq"] * p["dim"], (1e-5, 1e-6)),
    "mamba_scan": (_mamba_inputs, _mamba_reference, lambda p: 8.0 * p["seq"] * p["channels"] * p["state"], (1e-4, 1e-4)),
    "trimul": (_trimul_inputs, _trimul_reference, lambda p: 2.0 * p["n"] ** 3 * p["hidden"] + 12.0 * p["n"] * p["n"] * p["c"] * p["hidden"], (1e-3, 1e-3)),
    "add_rmsnorm_matmul": (_add_rmsnorm_matmul_inputs, lambda x, r, w, W: _rmsnorm(x + r, w) @ W, _mm_flops, (1e-4, 1e-4)),
    "rmsnorm_matmul": (_rmsnorm_matmul_inputs, lambda x, w, W: _rmsnorm(x, w) @ W, _mm_flops, (1e-4, 1e-4)),
    "matmul_add_rmsnorm": (_matmul_add_rmsnorm_inputs, lambda x, W, r, w: _rmsnorm(x @ W + r, w), _mm_flops, (1e-4, 1e-4)),
    "lora": (_lora_inputs, lambda x, W, A, B: x @ W + (x @ A) @ B, lambda p: 2.0 * p["m"] * p["k"] * p["n"] + 2.0 * p["m"] * p["r"] * (p["k"] + p["n"]), (1e-4, 1e-4)),
    "swiglu": (_swiglu_inputs, lambda x, Wg, Wu: F.silu(x @ Wg) * (x @ Wu), lambda p: 4.0 * p["m"] * p["k"] * p["n"], (1e-4, 1e-4)),
}


def _time(fn, repeats):
    fn()  # warm-up (allocations, thread pool)
    best = math.inf
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best


def _check(name, out, ref, tol):
    require(isinstance(out, torch.Tensor), f"{name}: return a torch.Tensor (got {type(out).__name__})")
    require(tuple(out.shape) == tuple(ref.shape), f"{name}: output shape {tuple(out.shape)} differs from the reference {tuple(ref.shape)}")
    out = out.to(torch.float32)
    require(bool(torch.isfinite(out).all()), f"{name}: output contains NaN or infinite values")
    rtol, atol = tol
    scale = float(ref.abs().max()) or 1.0
    error = float((out - ref).abs().max())
    require(error <= atol * scale + rtol * scale, f"{name}: max abs error {error:.3e} exceeds tolerance {atol * scale + rtol * scale:.3e} (reference scale {scale:.3e})")
    return error


def kernel_score(module, ops, seed=0, repeats=3, score="speedup"):
    """Run every named operator of ``ops`` (list of {name, op, params}) from ``module`` and score it.

    ``score`` is ``"speedup"`` (geometric mean of reference time / candidate time,
    higher is better) or ``"tflops"`` (mean achieved TFLOPS of the candidate,
    higher is better; the AVO metric). A wrong or malformed output fails the
    whole evaluation.
    """
    _torch()
    results = []
    for entry in ops:
        name, op, params = entry["name"], entry["op"], entry.get("params", {})
        require(op in OPS, f"unknown operator {op}")
        make, reference, flops, tol = OPS[op]
        fn = getattr(module, name, None)
        require(callable(fn), f"candidate must define {name}(...)")
        inputs = make(seed, params)
        with torch.no_grad():
            ref = reference(*inputs)
            try:
                out = fn(*inputs)
            except CandidateError:
                raise
            except Exception as error:  # noqa: BLE001
                raise CandidateError(f"{name} raised {type(error).__name__}: {error}") from None
            error = _check(name, out, ref, tol)
            t_ref = _time(lambda: reference(*inputs), repeats)
            t_new = _time(lambda: fn(*inputs), repeats)
        work = float(flops(params))
        results.append({"name": name, "op": op, "reference_seconds": round(t_ref, 6), "candidate_seconds": round(t_new, 6), "speedup": t_ref / t_new,
                        "tflops": work / t_new / 1e12, "reference_tflops": work / t_ref / 1e12, "max_abs_error": error})
    if score == "tflops":
        value = float(np.mean([r["tflops"] for r in results]))
    else:
        value = float(np.exp(np.mean([np.log(r["speedup"]) for r in results])))
    return value, {"kernels": results, "threads": torch.get_num_threads(), "metric": score}
