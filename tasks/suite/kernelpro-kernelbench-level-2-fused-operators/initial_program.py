"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def gemm_bias_relu(a, b, bias):
    return torch.relu(a @ b + bias)


def conv_bn_relu(x, w, gamma, beta, mean, var):
    y = F.conv2d(x, w, padding=1)
    y = (y - mean[None, :, None, None]) / torch.sqrt(var[None, :, None, None] + 1e-5) * gamma[None, :, None, None] + beta[None, :, None, None]
    return torch.relu(y)


def matmul_layer_norm(a, b, w, bias):
    return F.layer_norm(a @ b, (b.shape[1],), w, bias)
# EVOLVE-BLOCK-END
