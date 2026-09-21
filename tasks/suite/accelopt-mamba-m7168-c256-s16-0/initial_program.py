"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def mamba_scan(u, delta, A, B, C, D):
    h = torch.zeros(u.shape[1], A.shape[1])
    ys = []
    for t in range(u.shape[0]):
        dA = torch.exp(delta[t][:, None] * A)
        dB = delta[t][:, None] * B[t][None, :]
        h = dA * h + dB * u[t][:, None]
        ys.append(h @ C[t] + D * u[t])
    return torch.stack(ys)
# EVOLVE-BLOCK-END
