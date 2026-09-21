"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def bmm_softmax(a, b):
    return torch.softmax(torch.bmm(a, b), dim=-1)
# EVOLVE-BLOCK-END
