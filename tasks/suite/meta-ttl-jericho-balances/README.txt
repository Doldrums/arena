# Jericho Balances

**Paper:** Learning to Learn-at-Test-Time: Language Agents with Learnable Adaptation Policies (https://arxiv.org/pdf/2604.00830)\
**Task id:** `meta-ttl-jericho-balances`\
**Protocol:** `recreated`\
**Direction:** maximize\

## Task

Jericho Balances task evaluated in Learning to Learn-at-Test-Time: Language Agents with Learnable Adaptation Policies.

Benchmark named in the paper: Jericho. Paper metric: W-AUC and episode game score.

## Candidate interface

act(observation, valid_actions, history, llm) -> str: the next text command. observation is the game text after the last command, valid_actions the parser-accepted commands for the current state, history the list of (action, observation, reward) so far, llm the cached budgeted OpenRouter client (llm(prompt, system=None, max_tokens=None) -> str). Score: final game score / maximum score after STEPS commands, averaged over RUNS seeded plays. Higher is better.

Parameters: `{"game": "balances", "engine": "jericho", "steps": 40, "runs": 1}`

## Labels

Scientific contribution: `benchmark` (tier 3); artifact `agent`, domain `games`, data `public_benchmark`, verification `sampled`, reference `none`, resources `model_api`. See [docs/LABELS.md](../../docs/LABELS.md).

## Importance to science

A task is important to science when it addresses a substantive scientific or real-world problem, and a cited research paper's main objective is to solve that problem or advance understanding of it. The evidence must explain why the problem matters and how the local task represents it. Using a task to evaluate an agent, framework, or general-purpose model, or citing only a benchmark, dataset, or tool, does not establish scientific importance.

Evidence status: **unreviewed**.


No qualifying paper whose main objective is this underlying scientific or real-world problem has been established in the evidence registry. A task's use in an agent/framework evaluation is insufficient. This label describes the available evidence, not proof that the task has no scientific value.

## Evaluation protocol

Reimplemented in this repository from the paper's task description; instances are generated locally with a fixed seed, so scores are comparable within the suite but not with the paper's numbers.

- Game file fetched by scripts/prepare_game_data.py from the Jericho suite (pinned SHA-256).
- Recreated agent protocol: the game engine (Jericho z-machine games from the Jericho suite, or TextWorld games generated locally) is the paper's environment, but the step budget, prompt format and the absence of the papers' test-time-learning or BALROG wrappers are local choices; scores are comparable within the suite only. Model calls go through the budgeted client (default budget 0.25 USD per evaluation).

## Run

```
python evaluator.py initial_program.py
```

The evaluator prints a JSON result with `combined_score` (the value SCiEL maximizes), `score` (the task metric in its own direction), `valid` and `error`. `config.yaml` is a ready SCiEL configuration; copied SCiEL examples keep their upstream configuration.

## Requirements

- `py:numpy`
- `env:OPENROUTER_API_KEY`
- `network:openrouter`
- `py:jericho`
- `file:data/jericho/balances.z5`

## Sources

- paper: https://arxiv.org/pdf/2604.00830 (Section 4.1)
- repository: https://github.com/zzzlou/meta-ttl/tree/b72db4b77e9ae01aec1cbfd36ae0edae902b6468 (jericho_agent/evaluate.py)

## Limitations

- No complete, verified execution adapter has been established for this exact task; this package is an explicit implementation gap.
