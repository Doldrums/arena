"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def gemm_split_k(a, b):
    return a @ b
# EVOLVE-BLOCK-END
