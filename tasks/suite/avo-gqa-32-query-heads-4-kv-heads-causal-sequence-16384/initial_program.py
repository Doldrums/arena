"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F


def attention(q, k, v, causal):
    # Naive seed: materialise the full score matrix per head in float32 (memory heavy, no tiling).
    b, hq, s, d = q.shape
    if k.shape[1] != hq:
        rep = hq // k.shape[1]
        k = k.repeat_interleave(rep, dim=1)
        v = v.repeat_interleave(rep, dim=1)
    out = torch.empty_like(q)
    for h in range(hq):
        scores = q[:, h] @ k[:, h].transpose(-1, -2) / math.sqrt(d)
        if causal:
            scores = scores.masked_fill(torch.triu(torch.ones(s, s, dtype=torch.bool), 1), float('-inf'))
        out[:, h] = torch.softmax(scores, dim=-1) @ v[:, h]
    return out
# EVOLVE-BLOCK-END
