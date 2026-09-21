"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def layer_norm(x, w, b):
    return F.layer_norm(x, (x.shape[-1],), w, b)
# EVOLVE-BLOCK-END
