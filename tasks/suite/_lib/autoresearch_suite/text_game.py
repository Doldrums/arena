"""Language agents in text-adventure environments (Jericho games and TextWorld), recreated protocol.

The papers (Learning to Learn at Test Time, BALROG/HSI) evaluate an LLM agent
that plays interactive-fiction games. The candidate is the agent policy::

    act(observation, valid_actions, history, llm) -> str

``observation`` is the game text after the last action, ``valid_actions`` the
parser-accepted commands Jericho or TextWorld reports for the current state,
``history`` the list of (action, observation, reward) tuples so far and ``llm``
the suite's cached, budgeted OpenRouter client. The agent returns the next
command; an unknown command is still sent to the game (the parser answers).
The score is the game score at the end of a fixed step budget divided by the
game's maximum score, averaged over the configured runs. Game files are fetched
by ``scripts/prepare_game_data.py`` (Jericho suite ROMs pinned by SHA-256;
TextWorld games generated locally with fixed seeds).
"""
from __future__ import annotations

from arena_task_paths import data_root

from pathlib import Path

from .runtime import CandidateError, require

DATA = data_root()
JERICHO_GAMES = {"zork1": {"file": "zork1.z5", "max_score": 350}, "zork3": {"file": "zork3.z5", "max_score": 7}, "detective": {"file": "detective.z5", "max_score": 360},
                 "library": {"file": "library.z5", "max_score": 30}, "balances": {"file": "balances.z5", "max_score": 51}, "temple": {"file": "temple.z5", "max_score": 35}}
TEXTWORLD_GAMES = {"treasure_hunter": {"file": "treasure_hunter.z8"}, "coin_collector": {"file": "coin_collector.z8"}, "cooking": {"file": "cooking.z8"}}


def _call_agent(act, observation, valid_actions, history, llm):
    try:
        action = act(observation, list(valid_actions), list(history), llm)
    except CandidateError:
        raise
    except Exception as error:  # noqa: BLE001
        raise CandidateError(f"act raised {type(error).__name__}: {error}") from None
    require(isinstance(action, str) and action.strip(), "act must return a non-empty command string")
    return action.strip()[:200]


def play_jericho(act, game, llm, steps=40, seed=0):
    try:
        from jericho import FrotzEnv
    except ImportError as error:
        raise CandidateError(f"jericho is required: {error}") from None
    spec = JERICHO_GAMES[game]
    path = DATA / "jericho" / spec["file"]
    require(path.is_file(), f"game file missing: {path} (run python3 scripts/prepare_game_data.py)")
    env = FrotzEnv(str(path), seed=seed)
    observation, info = env.reset()
    history, total = [], 0.0
    for _ in range(steps):
        valid = env.get_valid_actions()
        action = _call_agent(act, observation, valid, history, llm)
        observation, reward, done, info = env.step(action)
        total += float(reward)
        history.append((action, observation, float(reward)))
        if done:
            break
    env.close()
    maximum = float(env.get_max_score() or spec["max_score"])
    return {"game": game, "score": float(info.get("score", total)), "max_score": maximum, "steps": len(history), "normalized": max(0.0, float(info.get("score", total))) / maximum}


def play_textworld(act, game, llm, steps=40, seed=0):
    try:
        import textworld
        import textworld.gym  # noqa: F401
    except ImportError as error:
        raise CandidateError(f"textworld is required: {error}") from None
    spec = TEXTWORLD_GAMES[game]
    path = DATA / "textworld" / spec["file"]
    require(path.is_file(), f"game file missing: {path} (run python3 scripts/prepare_game_data.py)")
    infos = textworld.EnvInfos(admissible_commands=True, score=True, max_score=True, won=True, lost=True)
    env = textworld.start(str(path), infos)
    state = env.reset()
    observation, history, total = state.feedback, [], 0.0
    maximum = float(state.max_score or 1.0)
    done = False
    for _ in range(steps):
        if done:
            break
        action = _call_agent(act, observation, state.admissible_commands or [], history, llm)
        state, reward, done = env.step(action)
        observation = state.feedback
        total += float(reward)
        history.append((action, observation, float(reward)))
    env.close()
    return {"game": game, "score": float(state.score), "max_score": maximum, "steps": len(history), "normalized": max(0.0, float(state.score)) / maximum, "won": bool(state.won)}


def text_game_score(act, game, engine, steps=40, runs=1, model=None, budget_usd=None):
    """Mean normalized game score of the agent over ``runs`` seeded plays (higher is better)."""
    from .llm import BUDGET_USD, DEFAULT_MODEL, LLM
    llm = LLM(model=model or DEFAULT_MODEL, budget_usd=BUDGET_USD if budget_usd is None else budget_usd)
    play = play_jericho if engine == "jericho" else play_textworld
    rows = [play(act, game, llm, steps=steps, seed=seed) for seed in range(runs)]
    return float(sum(r["normalized"] for r in rows) / len(rows)), {"runs": rows, "usage": llm.usage()}
