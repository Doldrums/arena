"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def grouped_gemm_weight_gradient(x, dy, sizes):
    out, start = [], 0
    for size in sizes.tolist():
        out.append(x[start:start + size].T @ dy[start:start + size])
        start += size
    return torch.stack(out)
# EVOLVE-BLOCK-END
