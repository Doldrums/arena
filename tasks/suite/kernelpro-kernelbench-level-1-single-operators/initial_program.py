"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import math
import torch
import torch.nn.functional as F

def matmul(a, b):
    return a @ b


def softmax(x):
    return torch.softmax(x, dim=-1)


def layer_norm(x, w, b):
    return F.layer_norm(x, (x.shape[-1],), w, b)


def conv2d(x, w):
    return F.conv2d(x, w, padding=1)


def relu(x):
    return torch.relu(x)
# EVOLVE-BLOCK-END
