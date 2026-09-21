# Extracted from the MIT-licensed ReEvo prompts/cvrp_lehd/seed_func.txt.
import torch
def heuristics_v1(distance_matrix: torch.Tensor, demands: torch.Tensor) -> torch.Tensor:
    """A trivial implementation to improve upon."""
    return torch.zeros_like(distance_matrix)
