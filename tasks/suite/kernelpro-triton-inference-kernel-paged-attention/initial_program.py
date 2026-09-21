"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def paged_attention(q, k_cache, v_cache, tables, lengths):
    page = k_cache.shape[1]
    outputs = []
    for i in range(q.shape[0]):
        n = int(lengths[i])
        blocks = tables[i, : math.ceil(n / page)]
        k = k_cache[blocks].reshape(-1, k_cache.shape[2], k_cache.shape[3])[:n]
        v = v_cache[blocks].reshape(-1, v_cache.shape[2], v_cache.shape[3])[:n]
        scores = torch.einsum('hd,nhd->hn', q[i], k) / math.sqrt(q.shape[-1])
        outputs.append(torch.einsum('hn,nhd->hd', torch.softmax(scores, dim=-1), v))
    return torch.stack(outputs)
# EVOLVE-BLOCK-END
