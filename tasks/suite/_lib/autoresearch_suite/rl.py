"""Reinforcement-learning algorithm design on Gymnasium environments (recreated protocol).

The paper family evolves the learning algorithm (update rule, loss, exploration)
rather than a policy. The candidate exposes

    class Agent:
        def __init__(self, observation_space, action_space, seed): ...
        def act(self, observation, explore=True) -> action
        def observe(self, observation, action, reward, next_observation, terminated, truncated): ...

The evaluator trains the agent for a fixed number of environment steps on a
named Gymnasium task and reports the mean undiscounted return of evaluation
episodes with exploration off. Budgets are deliberately small (CPU, minutes);
scores are comparable within the suite, not with the papers' multi-million-step
runs. MuJoCo tasks need the ``mujoco`` package (pip); Box2D tasks need
``gymnasium[box2d]`` (swig).
"""
from __future__ import annotations

import numpy as np

from .runtime import CandidateError, require

TASKS = {
    "CartPole-v1": {"train_steps": 20000, "eval_episodes": 10, "extras": None},
    "MountainCar-v0": {"train_steps": 30000, "eval_episodes": 5, "extras": None},
    "Acrobot-v1": {"train_steps": 20000, "eval_episodes": 5, "extras": None},
    "LunarLander-v3": {"train_steps": 40000, "eval_episodes": 5, "extras": "box2d"},
    "InvertedPendulum-v4": {"train_steps": 20000, "eval_episodes": 5, "extras": "mujoco"},
    "Reacher-v4": {"train_steps": 20000, "eval_episodes": 5, "extras": "mujoco"},
    "Swimmer-v4": {"train_steps": 20000, "eval_episodes": 3, "extras": "mujoco"},
    "Hopper-v4": {"train_steps": 20000, "eval_episodes": 3, "extras": "mujoco"},
    "Walker2d-v4": {"train_steps": 20000, "eval_episodes": 3, "extras": "mujoco"},
    "HalfCheetah-v5": {"train_steps": 20000, "eval_episodes": 3, "extras": "mujoco"},
}


def make_env(name, seed):
    try:
        import gymnasium as gym
    except ImportError as error:
        raise CandidateError(f"gymnasium is required: {error}") from None
    try:
        env = gym.make(name)
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"cannot create {name}: {type(error).__name__}: {error}") from None
    env.reset(seed=seed)
    env.action_space.seed(seed)
    return env


def rl_score(agent_class, task, seeds=(0,), train_steps=None, eval_episodes=None, max_episode_steps=1000):
    """Mean evaluation return after ``train_steps`` interaction steps (higher is better)."""
    spec = TASKS[task]
    train_steps = train_steps or spec["train_steps"]
    eval_episodes = eval_episodes or spec["eval_episodes"]
    returns = []
    for seed in seeds:
        env = make_env(task, seed)
        try:
            agent = agent_class(env.observation_space, env.action_space, seed)
        except Exception as error:  # noqa: BLE001
            raise CandidateError(f"Agent construction failed: {type(error).__name__}: {error}") from None
        observation, _ = env.reset(seed=seed)
        steps = 0
        while steps < train_steps:
            try:
                action = agent.act(observation, explore=True)
            except Exception as error:  # noqa: BLE001
                raise CandidateError(f"act raised {type(error).__name__}: {error}") from None
            require(env.action_space.contains(_cast_action(action, env.action_space)), "act returned an action outside the action space")
            next_observation, reward, terminated, truncated, _ = env.step(_cast_action(action, env.action_space))
            try:
                agent.observe(observation, action, float(reward), next_observation, bool(terminated), bool(truncated))
            except Exception as error:  # noqa: BLE001
                raise CandidateError(f"observe raised {type(error).__name__}: {error}") from None
            observation = next_observation
            steps += 1
            if terminated or truncated:
                observation, _ = env.reset()
        for episode in range(eval_episodes):
            observation, _ = env.reset(seed=10_000 + seed * 100 + episode)
            total = 0.0
            for _ in range(max_episode_steps):
                action = _cast_action(agent.act(observation, explore=False), env.action_space)
                observation, reward, terminated, truncated, _ = env.step(action)
                total += float(reward)
                if terminated or truncated:
                    break
            returns.append(total)
        env.close()
    require(all(np.isfinite(returns)), "non-finite return")
    return float(np.mean(returns))


def _cast_action(action, space):
    import gymnasium as gym
    if isinstance(space, gym.spaces.Discrete):
        return int(np.asarray(action).ravel()[0])
    return np.clip(np.asarray(action, dtype=np.float32).reshape(space.shape), space.low, space.high)
