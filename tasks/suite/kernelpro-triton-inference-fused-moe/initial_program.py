"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def fused_moe(x, gate_w, w1, w2, top_k):
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
# EVOLVE-BLOCK-END
