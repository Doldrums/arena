"""Recreated differentiable expected improvement per cost baseline.

The released constant utility seed has no gradient and is marked unused by
the authors. This baseline obeys their exact utility signature and BO driver.
"""
import torch


def utility(train_x, train_y, best_x, best_y, test_x, mean_test_y,
            std_test_y, cost_test_y, budget_used, budget_total):
    sigma = std_test_y.clamp_min(1e-9)
    improvement = mean_test_y - best_y
    z = improvement / sigma
    normal = torch.distributions.Normal(torch.zeros_like(z), torch.ones_like(z))
    ei = improvement * normal.cdf(z) + sigma * torch.exp(normal.log_prob(z))
    return (ei / cost_test_y.clamp_min(1e-9)).squeeze(-1)
