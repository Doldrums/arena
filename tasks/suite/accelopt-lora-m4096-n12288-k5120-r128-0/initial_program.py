"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def lora(x, W, A, B):
    return x @ W + (x @ A) @ B
# EVOLVE-BLOCK-END
