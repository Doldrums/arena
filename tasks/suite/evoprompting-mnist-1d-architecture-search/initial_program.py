"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import torch


def build_model():
    # Two-layer MLP seed (about 6,500 parameters).
    return torch.nn.Sequential(torch.nn.Linear(40, 128), torch.nn.ReLU(), torch.nn.Linear(128, 10))
# EVOLVE-BLOCK-END
