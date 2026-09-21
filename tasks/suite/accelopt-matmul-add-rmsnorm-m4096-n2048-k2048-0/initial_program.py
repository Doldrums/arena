"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def matmul_add_rmsnorm(x, W, r, w):
    y = x @ W + r
    return y * torch.rsqrt(y.pow(2).mean(-1, keepdim=True) + 1e-6) * w
# EVOLVE-BLOCK-END
