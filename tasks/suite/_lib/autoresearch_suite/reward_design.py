"""Reward-function design on MetaWorld manipulation tasks (Text2Reward family, recreated protocol).

The paper evolves a dense reward function for a robot task and trains a policy
with it; the score is the task's own success rate. The candidate exposes

    reward(observation, action, next_observation, info) -> float

where ``info`` is MetaWorld's step info (``success``, ``near_object``,
``grasp_reward`` and so on). The evaluator trains a linear Gaussian policy with
the cross-entropy method for a fixed number of environment steps using the
candidate reward, then measures the success rate with exploration off.
Budgets are small (CPU, about a minute); scores are comparable within the
suite, not with the papers' SAC/PPO runs. Requires ``metaworld`` (MetaWorld v3,
MuJoCo) which runs on any CPU.
"""
from __future__ import annotations

import numpy as np

from .runtime import CandidateError, require


def make_env(task, seed):
    try:
        import gymnasium as gym
        import metaworld  # noqa: F401 - registers the Meta-World namespace
    except ImportError as error:
        raise CandidateError(f"metaworld is required: {error}") from None
    name = task if task.endswith("-v3") else task.rsplit("-v", 1)[0] + "-v3"
    try:
        env = gym.make("Meta-World/MT1", env_name=name, seed=seed, max_episode_steps=200)
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"cannot create MetaWorld task {name}: {type(error).__name__}: {error}") from None
    return env


def _rollout(env, policy, reward_fn, seed, horizon=200, explore_noise=0.0, rng=None):
    observation, _ = env.reset(seed=seed)
    total, success = 0.0, 0.0
    for _ in range(horizon):
        action = policy(observation)
        if explore_noise and rng is not None:
            action = action + explore_noise * rng.standard_normal(action.shape)
        action = np.clip(action, env.action_space.low, env.action_space.high).astype(np.float32)
        next_observation, _, terminated, truncated, info = env.step(action)
        try:
            value = float(reward_fn(np.array(observation), np.array(action), np.array(next_observation), dict(info)))
        except CandidateError:
            raise
        except Exception as error:  # noqa: BLE001
            raise CandidateError(f"reward raised {type(error).__name__}: {error}") from None
        require(np.isfinite(value), "reward must be finite")
        total += value
        success = max(success, float(info.get("success", 0.0)))
        observation = next_observation
        if terminated or truncated:
            break
    return total, success


def reward_design_score(reward_fn, task, seed=0, iterations=6, population=16, elite=4, eval_episodes=5):
    """Success rate of a CEM-trained linear policy under the candidate reward. Higher is better."""
    env = make_env(task, seed)
    rng = np.random.default_rng(seed)
    obs_dim, act_dim = int(np.prod(env.observation_space.shape)), int(np.prod(env.action_space.shape))
    mean = np.zeros((obs_dim + 1) * act_dim)
    std = np.full_like(mean, 0.1)

    def policy_from(theta):
        W = theta[: obs_dim * act_dim].reshape(obs_dim, act_dim)
        b = theta[obs_dim * act_dim:]
        return lambda observation: np.tanh(np.asarray(observation, dtype=np.float64) @ W + b)

    episode = 0
    for _ in range(iterations):
        thetas = mean + std * rng.standard_normal((population, mean.size))
        scores = []
        for theta in thetas:
            total, _ = _rollout(env, policy_from(theta), reward_fn, seed=seed * 1000 + episode, rng=rng)
            episode += 1
            scores.append(total)
        order = np.argsort(scores)[::-1][:elite]
        mean = thetas[order].mean(axis=0)
        std = thetas[order].std(axis=0) + 0.02
    policy = policy_from(mean)
    successes = [_rollout(env, policy, reward_fn, seed=50_000 + seed * 100 + i)[1] for i in range(eval_episodes)]
    env.close()
    return float(np.mean(successes))


# ---------------------------------------------------------------------------
# Gymnasium MuJoCo analogues (Eureka / DrEureka / STRIDE / REvolve / HyperAgents / Text2Reward Gym tasks)
# ---------------------------------------------------------------------------

def _rotation_total(angles):
    unwrapped = np.unwrap(np.asarray(angles))
    return float(unwrapped[-1] - unwrapped[0]) if len(unwrapped) > 1 else 0.0


def _leg_wave(trace):
    trace = np.asarray(trace)
    if trace.ndim != 2 or len(trace) < 2:
        return 0.0
    stds = trace.std(axis=0)
    return float(stds[0] - stds[1:].mean())


GYM_TASKS = {
    # name: env id, fitness (higher is better; the task's own success notion), description
    "cartpole": ("InvertedPendulum-v5", lambda tr: tr["steps"] / 1000.0, "fraction of a 1000-step episode the pole stays balanced"),
    "ant_forward": ("Ant-v5", lambda tr: float(np.mean(tr["x_velocity"])), "mean forward (x) velocity"),
    "ant_lie_down": ("Ant-v5", lambda tr: float(np.mean(np.asarray(tr["torso_z"]) < 0.35)), "fraction of steps with the torso below 0.35"),
    "ant_wave_leg": ("Ant-v5", lambda tr: _leg_wave(tr["hips"]), "oscillation of the front-left hip minus the other hips' motion"),
    "ant_torso_height": ("Ant-v5", lambda tr: float(np.mean(np.abs(np.asarray(tr["torso_z"]) - 0.75) < 0.1)), "fraction of steps with the torso height within 0.75 +/- 0.1"),
    "hopper_forward": ("Hopper-v5", lambda tr: float(np.mean(tr["x_velocity"])), "mean forward velocity"),
    "hopper_back_flip": ("Hopper-v5", lambda tr: max(0.0, _rotation_total(tr["torso_angle"]) / (2 * np.pi)), "torso rotations in the positive angle direction"),
    "hopper_front_flip": ("Hopper-v5", lambda tr: max(0.0, -_rotation_total(tr["torso_angle"]) / (2 * np.pi)), "torso rotations in the negative angle direction"),
    "humanoid_forward": ("Humanoid-v5", lambda tr: float(np.mean(tr["x_velocity"])), "mean forward velocity"),
    "humanoid_sprint": ("Humanoid-v5", lambda tr: float(np.max(np.cumsum(tr["x_velocity"]) * 0.015)) if len(tr["x_velocity"]) else 0.0, "distance covered in the x direction"),
    "adroit_door": ("AdroitHandDoor-v1", lambda tr: float(np.max(tr["success"])) if len(tr["success"]) else 0.0, "door opened (environment success flag)"),
}


def make_gym_env(env_id, seed):
    try:
        import gymnasium as gym
    except ImportError as error:
        raise CandidateError(f"gymnasium is required: {error}") from None
    if env_id.startswith("Adroit"):
        try:
            import gymnasium_robotics
            gym.register_envs(gymnasium_robotics)
        except ImportError as error:
            raise CandidateError(f"gymnasium-robotics is required: {error}") from None
    try:
        env = gym.make(env_id, max_episode_steps=200)
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"cannot create {env_id}: {type(error).__name__}: {error}") from None
    env.reset(seed=seed)
    env.action_space.seed(seed)
    return env


def _gym_rollout(env, policy, reward_fn, seed, horizon=200, explore_noise=0.0, rng=None):
    observation, _ = env.reset(seed=seed)
    trace = {"x_velocity": [], "torso_z": [], "torso_angle": [], "hips": [], "success": [], "steps": 0}
    data = env.unwrapped.data if hasattr(env.unwrapped, "data") else None
    total = 0.0
    for _ in range(horizon):
        action = policy(observation)
        if explore_noise and rng is not None:
            action = action + explore_noise * rng.standard_normal(action.shape)
        action = np.clip(action, env.action_space.low, env.action_space.high).astype(np.float32)
        next_observation, _, terminated, truncated, info = env.step(action)
        try:
            value = float(reward_fn(np.array(observation), np.array(action), np.array(next_observation), dict(info)))
        except CandidateError:
            raise
        except Exception as error:  # noqa: BLE001
            raise CandidateError(f"reward raised {type(error).__name__}: {error}") from None
        require(np.isfinite(value), "reward must be finite")
        total += value
        trace["steps"] += 1
        trace["x_velocity"].append(float(info.get("x_velocity", 0.0)))
        trace["success"].append(float(info.get("success", 0.0)))
        if data is not None:
            qpos = np.array(data.qpos)
            trace["torso_z"].append(float(qpos[2]) if len(qpos) > 2 else 0.0)
            trace["torso_angle"].append(float(qpos[2]) if len(qpos) == 6 else 0.0)  # Hopper: (x, z, angle, ...) -> index 2 is the torso angle
            if len(qpos) >= 15:  # Ant: hip joints at qpos[7], [9], [11], [13]
                trace["hips"].append([float(qpos[7]), float(qpos[9]), float(qpos[11]), float(qpos[13])])
        observation = next_observation
        if terminated or truncated:
            break
    if data is not None and len(np.array(data.qpos)) == 6:  # Hopper: torso height is qpos[1]
        trace["torso_z"] = []
    return total, trace


def gym_reward_design_score(reward_fn, task, seed=0, iterations=6, population=16, elite=4, eval_episodes=5):
    """Task fitness (see GYM_TASKS) of a CEM-trained linear policy under the candidate reward. Higher is better."""
    env_id, fitness, _ = GYM_TASKS[task]
    env = make_gym_env(env_id, seed)
    rng = np.random.default_rng(seed)
    obs_dim, act_dim = int(np.prod(env.observation_space.shape)), int(np.prod(env.action_space.shape))
    mean = np.zeros((obs_dim + 1) * act_dim)
    std = np.full_like(mean, 0.1)

    def policy_from(theta):
        W = theta[: obs_dim * act_dim].reshape(obs_dim, act_dim)
        b = theta[obs_dim * act_dim:]
        return lambda observation: np.tanh(np.asarray(observation, dtype=np.float64) @ W + b)

    episode = 0
    for _ in range(iterations):
        thetas = mean + std * rng.standard_normal((population, mean.size))
        scores = []
        for theta in thetas:
            total, _ = _gym_rollout(env, policy_from(theta), reward_fn, seed=seed * 1000 + episode, rng=rng)
            episode += 1
            scores.append(total)
        order = np.argsort(scores)[::-1][:elite]
        mean = thetas[order].mean(axis=0)
        std = thetas[order].std(axis=0) + 0.02
    policy = policy_from(mean)
    values = [fitness(_gym_rollout(env, policy, reward_fn, seed=50_000 + seed * 100 + i)[1]) for i in range(eval_episodes)]
    env.close()
    return float(np.mean(values)), {"fitness": GYM_TASKS[task][2], "environment": env_id, "episodes": values}
