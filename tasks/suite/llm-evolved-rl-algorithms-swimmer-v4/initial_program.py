"""Initial program for the suite task; SCiEL evolves the EVOLVE-BLOCK."""
# EVOLVE-BLOCK-START
import numpy as np


class Agent:
    """Linear REINFORCE baseline: softmax policy for discrete actions, tanh-Gaussian for continuous ones."""

    def __init__(self, observation_space, action_space, seed):
        self.rng = np.random.default_rng(seed)
        self.discrete = hasattr(action_space, "n")
        self.obs_dim = int(np.prod(observation_space.shape))
        self.act_dim = int(action_space.n) if self.discrete else int(np.prod(action_space.shape))
        self.W = self.rng.normal(0, 0.01, (self.obs_dim, self.act_dim))
        self.b = np.zeros(self.act_dim)
        self.log_std = np.full(self.act_dim, -0.5)
        self.lr, self.gamma = 0.01, 0.99
        self.episode = []

    def act(self, observation, explore=True):
        x = np.asarray(observation, dtype=np.float64).ravel()
        logits = x @ self.W + self.b
        if self.discrete:
            if not explore:
                return int(np.argmax(logits))
            p = np.exp(logits - logits.max())
            p /= p.sum()
            return int(self.rng.choice(self.act_dim, p=p))
        mean = np.tanh(logits)
        return mean if not explore else mean + np.exp(self.log_std) * self.rng.standard_normal(self.act_dim)

    def observe(self, observation, action, reward, next_observation, terminated, truncated):
        self.episode.append((np.asarray(observation, dtype=np.float64).ravel(), action, reward))
        if terminated or truncated:
            self._update()
            self.episode = []

    def _update(self):
        G, returns = 0.0, []
        for _, _, r in reversed(self.episode):
            G = r + self.gamma * G
            returns.append(G)
        returns = np.array(returns[::-1])
        returns = (returns - returns.mean()) / (returns.std() + 1e-8)
        for (x, a, _), g in zip(self.episode, returns):
            logits = x @ self.W + self.b
            if self.discrete:
                p = np.exp(logits - logits.max())
                p /= p.sum()
                grad = -p
                grad[a] += 1.0
            else:
                mean = np.tanh(logits)
                grad = (np.asarray(a) - mean) / np.exp(2 * self.log_std) * (1 - mean ** 2)
            self.W += self.lr * g * np.outer(x, grad)
            self.b += self.lr * g * grad
# EVOLVE-BLOCK-END
