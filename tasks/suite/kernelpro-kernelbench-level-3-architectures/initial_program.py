"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def mlp_block(x, w1, b1, w2, b2):
    return F.gelu(x @ w1 + b1) @ w2 + b2


def transformer_block(x, wqkv, wo, ln_w, ln_b, w1, b1, w2, b2, heads):
    b, t, d = x.shape
    h = F.layer_norm(x, (d,), ln_w, ln_b)
    q, k, v = (h @ wqkv).split(d, dim=-1)
    q, k, v = (z.reshape(b, t, heads, d // heads).transpose(1, 2) for z in (q, k, v))
    a = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(b, t, d) @ wo
    x = x + a
    h = F.layer_norm(x, (d,), ln_w, ln_b)
    return x + F.gelu(h @ w1 + b1) @ w2 + b2
# EVOLVE-BLOCK-END
