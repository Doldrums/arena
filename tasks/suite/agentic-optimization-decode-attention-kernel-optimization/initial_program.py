"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def decode_attention(q, k, v):
    return F.scaled_dot_product_attention(q, k, v)
# EVOLVE-BLOCK-END
