"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def adamw(param, grad, m, v, step, lr, beta1, beta2, eps, wd):
    m2 = beta1 * m + (1 - beta1) * grad
    v2 = beta2 * v + (1 - beta2) * grad * grad
    m_hat = m2 / (1 - beta1 ** step)
    v_hat = v2 / (1 - beta2 ** step)
    return torch.stack([param * (1 - lr * wd) - lr * m_hat / (torch.sqrt(v_hat) + eps), m2, v2])
# EVOLVE-BLOCK-END
