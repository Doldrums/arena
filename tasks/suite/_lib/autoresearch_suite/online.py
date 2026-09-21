"""Sequential decision families: non-stationary contextual bandit (AEL harness, recreated)."""
from __future__ import annotations

import numpy as np

from .runtime import CandidateError, require


def bandit_score(policy_class, n_arms=5, dim=8, horizon=2000, drift_every=500, seeds=(0, 1, 2)):
    """Mean cumulative reward of ``Policy(n_arms, dim)`` with ``select(context) -> arm`` and ``update(context, arm, reward)``.

    Rewards are linear in the context with arm-specific weights that are
    redrawn every ``drift_every`` rounds (non-stationarity) plus Gaussian noise.
    Higher is better.
    """
    totals = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        weights = rng.standard_normal((n_arms, dim))
        try:
            policy = policy_class(n_arms, dim)
        except Exception as error:  # noqa: BLE001
            raise CandidateError(f"policy construction failed: {type(error).__name__}: {error}") from None
        total = 0.0
        for t in range(horizon):
            if t and t % drift_every == 0:
                weights = rng.standard_normal((n_arms, dim))
            context = rng.standard_normal(dim)
            try:
                arm = int(policy.select(context.copy()))
            except Exception as error:  # noqa: BLE001
                raise CandidateError(f"select raised {type(error).__name__}: {error}") from None
            require(0 <= arm < n_arms, "select must return an arm index")
            reward = float(weights[arm] @ context + 0.5 * rng.standard_normal())
            total += reward
            try:
                policy.update(context.copy(), arm, reward)
            except Exception as error:  # noqa: BLE001
                raise CandidateError(f"update raised {type(error).__name__}: {error}") from None
        totals.append(total / horizon)
    return float(np.mean(totals))
