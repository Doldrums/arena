"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def transpose_matmul(a, b):
    return a.T @ b
# EVOLVE-BLOCK-END
