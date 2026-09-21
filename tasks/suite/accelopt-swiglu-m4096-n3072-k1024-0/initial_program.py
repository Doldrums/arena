"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def swiglu(x, Wg, Wu):
    return F.silu(x @ Wg) * (x @ Wu)
# EVOLVE-BLOCK-END
