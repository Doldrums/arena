"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def swish(x):
    return x * torch.sigmoid(x)
# EVOLVE-BLOCK-END
