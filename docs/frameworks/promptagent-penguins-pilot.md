# PromptAgent native penguins pilot

`promptagent-penguins-gateway / penguins-mcts-pilot` runs the native PromptAgent MCTS at `XinyuanWangCS/PromptAgent@2edfc9e4462a6af97dc973442d074de9b3e876b2` (Apache-2.0). It is separate from the existing `promptagent / native-search` recipe. Templates remain blocked until operator review and deployment; offline protocol checks do not establish live model performance.

The benchmark is the repository's real `datasets/penguins_in_a_table.json`: 149 bundled BIG-bench examples, SHA256 `f743ab0bd8d500798fc0ab83fdd3547b924e9c1acb15ca11b65ac228c0ab557a`. No dataset download, synthetic replacement, embeddings or local model weights are needed. The example configuration supplies the initial penguin-table instruction. Native `tasks.bigbench.CustomTask` retains the table context, options, answer-tag parsing and exact accuracy reward.

Native `BaseTask.split_list_dataset` shuffles with seed 42, takes four held-out examples first, eight training examples next and four reward examples from the remaining tail. The driver records actual native split hashes and rejects size changes, duplicate observations, question overlap or train/reward/test overlap. It does not implement an alternative splitter.

## Search and held-out evaluation

The driver calls native `BaseAgent.run()` → `MCTS.search()`, preserving UCT selection, expansion, simulation, backpropagation, reward thresholds, textual gradient prompts, prompt parsing and path/node selection. The configuration is two iterations, expansion width 2, depth limit 2, minimum early-stop depth 1, UCT weight 2.5, training batch 2 and one requested new prompt per expansion. Both the base evaluator and optimizer use the same exact selected gateway model. Native training, reward and held-out loaders execute sequentially.

Native `MCTS.prepare_output()` ranks paths/nodes by search reward before testing their union on the held-out loader. Its selected node remains reward-based. A transport observer snapshots prompt/reward/visit state before the first held-out request and verifies the same state after the native run; it rejects any subsequent optimization/reward/training request. Test metrics may change, search state may not. Test accuracy must not be used for another selection pass. This is a small native integration protocol, not a full paper reproduction or canonical Arena evaluation.

An optimizer response without `<START>...<END>` blocks retains the native empty-child behavior. Additional blocks retain native parsing and consume the same global request allowance. Malformed task answers retain native accuracy-zero behavior. The adapter neither fabricates children nor substitutes a score on provider failure.

## Provider ports and limits

Two provider-only source edits are applied in the isolated runtime clone after whole-file hash checks:

1. `language_model/openai_model.py` imports the Arena provider constructor. The native model class, batch loop, `.strip()` behavior and backoff loop remain unchanged.
2. `language_model/__init__.py` disables unconditional imports/registrations for unused PaLM, Hugging Face, CTranslate2 and vLLM providers. The OpenAI registration and native lookup function remain unchanged. This explicit CPU/API profile does not claim those other providers are installed.

Config `api_key` fields contain `environment:base` / `environment:optim` role markers. The constructor obtains the actual scoped `OPENAI_API_KEY` only from worker memory and binds `http://127.0.0.1:8789/v1`; native configuration logging never sees the credential. Exact request/response model identity and one text choice are required. No alias/fallback is permitted.

The native unlimited retry loop is bounded at the SDK seam: one sanitized exception allows the native one-second backoff and one retry; a second failure raises a terminal exception outside the native `except Exception`. SDK retries are zero; HTTP redirects and ambient proxy settings are disabled. The shared global allowance is **96 actual SDK attempts**, including those native retries, with a 330-second per-request timeout. The template outer timeout is 2400 seconds, with 2 CPUs, 4096 MiB, 256 PIDs and one evaluation slot. These are request/resource/wall-time limits, not token or monetary budgets.

Native base/optimizer temperatures 0/1 are retained in the saved config and recorded as unenforced by the current gateway; they are omitted from its requests. Cost remains unknown. Provider errors/budget exhaustion produce stopped receipts and partial native nodes where available, never a completed result.

## Artifacts and board interpretation

`pilot-receipt.json` binds the source/preparation/port/config evidence and records status, actual node/iteration counts, the native selected node's `reward` and `heldout_accuracy`, and the frozen-state/split hashes. Both scores are native accuracy in `[0,1]`, each over four observations. Report that selected node; do not maximize across test scores.

`native-result.json` preserves upstream `all_nodes`, `all_paths`, `best_q_path`, `best_reward_path`, and reward-selected node records. Untested native nodes retain `test_metric=-1`; that sentinel is not a measured accuracy. `frozen-search-state.json` and `native-splits.json` are provenance artifacts. `gateway-usage.json` records actual attempts by phase (`training`, `reward`, `optimization`, `heldout`) and status, so retries are distinguishable from returned forward evaluations. Native logs contain prompts and benchmark responses and remain private artifacts.

## Preparation and offline evidence

The isolated VM environment is `/srv/arena/envs/promptagent-penguins-gateway`, Python3.11.16. The CPU/OpenAI path was installed with numpy 1.26.4, OpenAI 1.109.1, httpx 0.28.1, pytz 2025.2, PyYAML 6.0.3, tqdm 4.67.1, CPU torch 2.0.1 and pytest 8.4.2. The full resolved freeze and `uv pip check` are retained. Unused GPU/local-model packages in the upstream all-provider requirements are intentionally excluded. This is a recorded preparation environment, not a historical dependency lock.

Preparation lives under `/srv/arena/build/promptagent-penguins-preparation-20260921`; the immutable checkout is `/srv/arena/sources/promptagent`. The manifest hashes native source, license, requirements, example config and the complete packaged penguin dataset. Runtime plans bind this manifest, the dependency freeze, recipe, driver modules and executable. No live app/control configuration or queue admission is performed by these scripts.

```sh
python scripts/deployment/prepare_promptagent_pilots.py \
  --root /srv/arena --destination /absolute/new/templates \
  --dependencies /absolute/dependencies.txt
```

`check_promptagent_pilot.py` runs the real native classes and real modern OpenAI SDK with HTTPX MockTransport, blocking socket connections. All seven exact models are checked in fresh processes with `normal`, `retry` and `failure` scenarios. The normal fixture produces 48 SDK calls (8 training, 20 reward, 8 optimizer, 12 held-out), five native nodes and two iterations. One mock 429 yields 49 calls and completes through native backoff. Repeated 429 stops after two calls, writes a stopped receipt and produces no final result. Deterministic fixture accuracy is protocol evidence, not model or method performance.

```sh
/path/to/promptagent/python scripts/deployment/check_promptagent_pilot.py \
  --source /absolute/clean/promptagent --destination /absolute/new/fixture \
  --dependencies /absolute/dependencies.txt --model gpt-5.6-sol \
  --scenario normal
```

Focused tests additionally exercise global admission limits, successful retry counter reset, terminal response identity/count failures, disjoint split guards, unchanged frozen state and preservation of the legacy recipe identity. Offline mock runs do not claim service readiness or hostile-code isolation.
