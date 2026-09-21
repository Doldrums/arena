"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def trimul(x, mask, ln_w, ln_b, w_left, w_left_gate, w_right, w_right_gate, ln2_w, ln2_b, w_gate, w_out):
    h = F.layer_norm(x, (x.shape[-1],), ln_w, ln_b)
    m = mask[..., None]
    left = torch.sigmoid(h @ w_left_gate) * (h @ w_left) * m
    right = torch.sigmoid(h @ w_right_gate) * (h @ w_right) * m
    prod = torch.einsum('bikc,bjkc->bijc', left, right)
    prod = F.layer_norm(prod, (prod.shape[-1],), ln2_w, ln2_b)
    return torch.sigmoid(h @ w_gate) * (prod @ w_out)
# EVOLVE-BLOCK-END
