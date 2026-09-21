# Framework integration inventory — 2026-09-21

Implementation update later the same day: native launch/evaluation profiles
across the research library and scoped canonical bridges have since been added.
See the [current complete coverage audit](framework-coverage-20260921.md),
[the current integration guide](../docs/frameworks/README.md) and
[offline conformance evidence](framework-conformance-20260921.md). The registry
state described below is the **pre-implementation inventory snapshot**; it is
retained to distinguish the initial evidence from later adapter work.

This is an inventory for choosing an integration scope, not a claim that frameworks are connected. No framework was installed, imported, launched, or evaluated. No registry statuses were changed.

## What the existing registry actually establishes

- 99 participant records represent 98 research works plus SCiEL. They are not 99 independently runnable frameworks.
- Only SCiEL, DGM and ShinkaEvolve have Arena execution-registration repository pins. All three are `planned`, `adapter_status=not_implemented`, with empty `supported_protocols` and every capability false. All other records are literature entries. The aggregate reports zero integrations.
- 48 records have a reviewed `implementation` code link, referring to 46 distinct source locations after normalizing the shared SkyDiscover and EoH repositories. An implementation link alone does not verify a usable search loop, license, environment, observer, or task adapter.
- 12 records have only project/artifact links; 39 have no captured code/project/artifact link. The task-source bibliography separately lists repository provenance for 67 of the 98 works. Some of these are baselines, artifacts, inherited engines, or subsequently discovered repositories.
- The 15 task-collection supplements are source groups in the task catalog, not participants in these 99 records. The method-family label “AlphaEvolve / OpenEvolve” also does not register OpenEvolve as a participant.

Evidence: [aggregate](../registry/participants.json), [three execution declarations](../registry/participants/), [reviewed corpus capture](../registry/participant-corpus.json), [participant extraction/scoping rules](../src/arena/participant_corpus.py), and [pinned task-source bibliography](https://github.com/IMRUNya/autoresearch-tasks/blob/5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935/catalog/papers.json).

## Priority after choosing run vs observer integration

1. **SCiEL and ShinkaEvolve:** existing immutable Arena registrations, program/evaluator interfaces, and local source availability. SCiEL already has a separate read-only observer, which is not a native runner. Start by defining exactly which existing outputs to observe or which native whole-run command to control; then implement and test only the capabilities actually supported.
2. **SkyDiscover (AdaEvolve and EvoX through one engine), AgenticOptimization, EoH/ReEvo, GEPA:** practical next candidates because they expose explicit optimization or evaluator entrypoints. These still need Arena registrations, revision-specific interface checks, environments and conformance. One native engine can expose multiple named methods; do not duplicate the engine merely to match paper counts.
3. **DGM and agent/harness systems:** integrate with an agent-bundle/coding-episode contract rather than claiming universal single-file task support. DGM is already registered, but its Docker/benchmark lifecycle makes it a different integration from scalar evaluator program search.
4. **Reward-learning, GPU-kernel, simulator and dataset-heavy systems:** require task-specific dependencies, hardware and cost/budget controls. Prioritize only after the supported task set is explicit.
5. **Artifacts, missing code, anonymous sources, ambiguous identity/license:** retain as literature or discovery candidates until the implementation is verified. Do not mark them runnable to make the participant count match.

These priorities are engineering judgments from the interface and provenance evidence below, not measured runtime readiness.

## Directly checked official documentation (current docs, not proof of pinned compatibility)

- [ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve): current README exposes `shinka_launch`, `shinka_run`, `ShinkaEvolveRunner.run()`, evaluator scripts and `results_dir`; SQLite and WebUI logging remain primary outputs. The README says the unified runner replaced earlier runner classes, so check the exact Arena pin before selecting the API. License shown: Apache-2.0.
- [DGM](https://github.com/jennyzzt/dgm): `python DGM_outer.py`; default `output_dgm/`; Docker, SWE-bench/Polyglot setup and model credentials are documented. These are coding-agent experiments, not a generic scalar task callback. License shown: Apache-2.0.
- [SkyDiscover](https://github.com/skydiscover-ai/skydiscover): current README exposes `skydiscover optimize evaluator.py --search adaevolve` or `--search evox`, with model credentials. Both paper methods share the same native framework. The pinned task-source bibliography separately records the exact revision and Apache-2.0 license.
- [GEPA](https://github.com/gepa-ai/gepa): current README exposes `gepa.optimize`, an evaluator-based `optimize_anything` API, and `GEPAAdapter.evaluate` / `make_reflective_dataset`; `best_candidate` is a result object. A native adapter must preserve both score and feedback semantics. License shown: MIT.

Browser requests for the four exact GitHub `/tree/<pin>` pages failed. Current docs were accessible; no current-branch API is therefore claimed to exist at a pin merely because the README describes it. Existing pinned local metadata is labeled separately below.

## Complete inventory of 48 implementation-linked records

The table's pins, licenses and commands are copied from the task-source bibliography unless identified as an Arena registration. They are **provenance leads**, not newly verified runtime claims. `unknown` means no corresponding metadata was established in this review. A captured run command may be an evaluator, benchmark or web entrypoint instead of the native search loop; it must be checked before execution. All unregistered rows still need an immutable Arena registration, interface review, environment and conformance evidence. No repository-specific output format is inferred where it has not been inspected.


### Already registered, no implemented Arena runner

| Record | Integration identity / scope | Reviewed link | Task-source or Arena repository pin | Captured license | First captured command (not run) |
| --- | --- | --- | --- | --- | --- |
| dgm | Arena registration; capabilities false | [github.com/jennyzzt/dgm](https://github.com/jennyzzt/dgm) (implementation) | [github.com/jennyzzt/dgm](https://github.com/jennyzzt/dgm) @ `a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2` | Apache-2.0 | `python DGM_outer.py` |
| sciel | Arena registration; capabilities false | [github.com/Doldrums/sciel](https://github.com/Doldrums/sciel) (implementation) | [github.com/Doldrums/sciel](https://github.com/Doldrums/sciel) @ `0d67f813dd4ac21dee304f2b0de0b0ce59bf4157` (Arena registration; no task-source paper) | unknown | unknown |
| shinka | Arena registration; capabilities false | [github.com/SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) (implementation) | [github.com/SakanaAI/ShinkaEvolve](https://github.com/SakanaAI/ShinkaEvolve) @ `9912af12d423504b8d580f4179fd15f5f88b8c50` | Apache-2.0 | `python evaluate.py --program_path initial.py --results_dir results/manual_eval` |

### Shared engines, optimizer libraries and method components

| Record | Integration identity / scope | Reviewed link | Task-source or Arena repository pin | Captured license | First captured command (not run) |
| --- | --- | --- | --- | --- | --- |
| adaevolve | SkyDiscover search variant; same engine as EvoX | [github.com/skydiscover-ai/skydiscover.git](https://github.com/skydiscover-ai/skydiscover.git) (implementation) | [github.com/skydiscover-ai/skydiscover](https://github.com/skydiscover-ai/skydiscover) @ `0d932b690670a7e544388ad362e9876c8bd256a0` | Apache-2.0 | `uv run skydiscover optimize benchmarks/math/circle_packing/evaluator.py --search adaevolve --model gpt-5 -i 100` |
| evolcaf | EoH example/component, not a separate engine | [github.com/FeiLiu36/EoH/tree/main/examples/user_bo_caf](https://github.com/FeiLiu36/EoH/tree/main/examples/user_bo_caf) (implementation) | [github.com/FeiLiu36/EoH](https://github.com/FeiLiu36/EoH) @ `472545785c936dcfc863d2bc0d6109cf23c7ce62` | MIT | unknown |
| evox | SkyDiscover search variant; same engine as AdaEvolve | [github.com/skydiscover-ai/skydiscover](https://github.com/skydiscover-ai/skydiscover) (implementation) | [github.com/skydiscover-ai/skydiscover](https://github.com/skydiscover-ai/skydiscover) @ `0d932b690670a7e544388ad362e9876c8bd256a0` | Apache-2.0 | `uv run skydiscover optimize benchmarks/math/circle_packing/evaluator.py --search evox --model gpt-5 -i 100` |
| gepa | Optimizer library/API; native evaluator adapter needed | [github.com/gepa-ai/gepa](https://github.com/gepa-ai/gepa) (implementation) | [github.com/gepa-ai/gepa-artifact](https://github.com/gepa-ai/gepa-artifact) @ `cbefbc1aa0f43dd39874ec4bf42211365dbda42e`<br>[github.com/gepa-ai/gepa](https://github.com/gepa-ai/gepa) @ `15ee314f9c7d34ec153b809d401f42f55c4dcd76` | MIT<br>MIT | `uv run python -m scripts.generate_launch_commands`<br>unknown |
| llamea-bo | Optimizer research implementation; captured command is algorithm evaluation | [github.com/Ewendawi/LLaMEA-BO](https://github.com/Ewendawi/LLaMEA-BO) (implementation) | [github.com/Ewendawi/LLaMEA-BO](https://github.com/Ewendawi/LLaMEA-BO) @ `938b4d780aa0cbf9f7c941ebab61dadfa9157185` | MIT | `bash run_algo_evaluation.sh`; cwd `.` |
| meoh | Method implemented within LLM4AD, not a separately identified engine | [github.com/Optima-CityU/LLM4AD](https://github.com/Optima-CityU/LLM4AD) (implementation) | [github.com/Optima-CityU/LLM4AD](https://github.com/Optima-CityU/LLM4AD) @ `ffb6acf64497be93932c98d25369352efd3865cf` | unknown | unknown |
| protegi | LMOps prompt_optimization component | [github.com/microsoft/LMOps/tree/main/prompt_optimization](https://github.com/microsoft/LMOps/tree/main/prompt_optimization) (implementation) | [github.com/microsoft/LMOps](https://github.com/microsoft/LMOps) @ `6f53ef41c951de0962bbf27fe3f5819eabc8ce0e` | MIT | `python main.py --task liar --prompts prompts/liar.md --data_dir data/liar --out liar.out --evaluator ucb` |

### Program/heuristic/scientific search implementation candidates

| Record | Integration identity / scope | Reviewed link | Task-source or Arena repository pin | Captured license | First captured command (not run) |
| --- | --- | --- | --- | --- | --- |
| agentic-optimization | Native engine candidate; runnable loop/output contract unverified | [github.com/Junye-Pan/AgenticOptimization](https://github.com/Junye-Pan/AgenticOptimization) (implementation) | [github.com/Junye-Pan/AgenticOptimization](https://github.com/Junye-Pan/AgenticOptimization) @ `712b2fd4888c4b57fc08c1d2bdf4b1ca4c4517fb` | unknown | `PYTHONPATH=src python3 -m agentic_opt.web.app --state-root ao_state --db ao_state/control.sqlite3 --host 127.0.0.1 --port 5000` |
| base | Native engine candidate; runnable loop/output contract unverified | [github.com/keruiwu/self-evolving-allocation](https://github.com/keruiwu/self-evolving-allocation) (implementation) | [github.com/keruiwu/self-evolving-allocation](https://github.com/keruiwu/self-evolving-allocation) @ `ae7b5da1db39c0fd826adda7893c99d5bda5ac1b` | MIT | `python run_base.py --task cp --model qwen3-8b --algo ucb --T 64 --N 8 --n-arms 10` |
| codeevolve | Native engine candidate; runnable loop/output contract unverified | [github.com/inter-co/science-codeevolve](https://github.com/inter-co/science-codeevolve) (implementation) | [github.com/inter-co/science-codeevolve](https://github.com/inter-co/science-codeevolve) @ `c077959e1ab24b060aaa6d4c563bca2e9cbe8617` | Apache-2.0 | unknown |
| coevo | Native engine candidate; runnable loop/output contract unverified | [github.com/pgg3/CoEvo](https://github.com/pgg3/CoEvo) (implementation) | [github.com/pgg3/CoEvo](https://github.com/pgg3/CoEvo) @ `dcad65e9799961cf67cf29865ff41dda2902a808` | unknown | unknown |
| coral | Native engine candidate; runnable loop/output contract unverified | [github.com/Human-Agent-Society/CORAL](https://github.com/Human-Agent-Society/CORAL) (implementation) | [github.com/Human-Agent-Society/CORAL](https://github.com/Human-Agent-Society/CORAL) @ `0123dfb939b35228cf2c1fde224cd0561e727408` | Apache-2.0 | unknown |
| deliberate-evolution | Native engine candidate; runnable loop/output contract unverified | [github.com/Xinyu-Pang/Deliberate-Evolution](https://github.com/Xinyu-Pang/Deliberate-Evolution) (implementation) | [github.com/Xinyu-Pang/Deliberate-Evolution](https://github.com/Xinyu-Pang/Deliberate-Evolution) @ `18ae1f1c33a0dfa3c81298bba035036d3b23ecaf` | unknown | unknown |
| eoh | Native engine candidate; runnable loop/output contract unverified | [github.com/FeiLiu36/EoH](https://github.com/FeiLiu36/EoH) (implementation) | [github.com/FeiLiu36/EoH](https://github.com/FeiLiu36/EoH) @ `472545785c936dcfc863d2bc0d6109cf23c7ce62` | MIT | `python runEval.py` |
| eurekagent | Native engine candidate; runnable loop/output contract unverified | [github.com/THU-Team-Eureka/EurekAgent](https://github.com/THU-Team-Eureka/EurekAgent) (implementation) | [github.com/THU-Team-Eureka/EurekAgent](https://github.com/THU-Team-Eureka/EurekAgent) @ `fb96df897dfb99797a77623aa0dd9ee178fe89d2` | AGPL-3.0 | `bash examples/circle_packing/run.sh` |
| funsearch-re-implementation | Native engine candidate; runnable loop/output contract unverified | [github.com/kitft/funsearch](https://github.com/kitft/funsearch) (implementation) | [github.com/kitft/funsearch](https://github.com/kitft/funsearch) @ `cec37d84b474ea6bbd66f6defad8f5b5758449ff` | Apache-2.0 | unknown |
| hsevo | Native engine candidate; runnable loop/output contract unverified | [github.com/datphamvn/HSEvo](https://github.com/datphamvn/HSEvo) (implementation) | [github.com/datphamvn/HSEvo](https://github.com/datphamvn/HSEvo) @ `f3afffabc2b458fddf70a42a8678758039671297` | MIT | `python main.py algorithm=hsevo model=openai/gpt-4o-mini-2024-07-18 problem=bpp_online` |
| llm-lex | Native engine candidate; runnable loop/output contract unverified | [github.com/harveyThomas4692/llmlex](https://github.com/harveyThomas4692/llmlex) (implementation) | [github.com/harveyThomas4692/llmlex](https://github.com/harveyThomas4692/llmlex) @ `9f02b58c5efb6d3c973c2ad2552ecc3a57998f81` | unknown | unknown |
| loongflow | Native engine candidate; runnable loop/output contract unverified | [github.com/baidu-baige/LoongFlow](https://github.com/baidu-baige/LoongFlow) (implementation) | [github.com/baidu-baige/LoongFlow](https://github.com/baidu-baige/LoongFlow) @ `945c78bc1554f8281aac40320b3599bd68d528d7` | Apache-2.0 | unknown |
| mcts-ahd | Native engine candidate; runnable loop/output contract unverified | [github.com/zz1358m/MCTS-AHD-master/tree/main](https://github.com/zz1358m/MCTS-AHD-master/tree/main) (implementation) | [github.com/zz1358m/MCTS-AHD-master](https://github.com/zz1358m/MCTS-AHD-master) @ `ee9c4f424503c65a5fd2b899e6620ce86079fedb` | MIT | unknown |
| rankevolve | Native engine candidate; runnable loop/output contract unverified | [github.com/fangchenli/ranking-evolved](https://github.com/fangchenli/ranking-evolved) (implementation) | [github.com/fangchenli/ranking-evolved](https://github.com/fangchenli/ranking-evolved) @ `8f664bcd5123bac2397f0c1bfbdb347ca3233483` | MIT | unknown |
| the-station | Native engine candidate; runnable loop/output contract unverified | [github.com/dualverse-ai/station](https://github.com/dualverse-ai/station) (implementation); [dualverse-ai.github.io/station_data/](https://dualverse-ai.github.io/station_data/) (artifact) | [github.com/dualverse-ai/station](https://github.com/dualverse-ai/station) @ `782088e561998bf357d95a838a0566a8229425d9` | Apache-2.0 | unknown |

### Agent, harness, workflow and environment-search implementation candidates

| Record | Integration identity / scope | Reviewed link | Task-source or Arena repository pin | Captured license | First captured command (not run) |
| --- | --- | --- | --- | --- | --- |
| adas | Native engine candidate; runnable loop/output contract unverified | [github.com/ShengranHu/ADAS](https://github.com/ShengranHu/ADAS) (implementation) | [github.com/ShengranHu/ADAS](https://github.com/ShengranHu/ADAS) @ `2702bee8fefda42255efc5be9f60e3bd3db96ae4` | Apache-2.0 | `python _arc/search.py --val_data_path dataset/sampled_arc_val_data.pkl --test_data_path dataset/sampled_arc_test_data.pkl` |
| ael-harness | Native engine candidate; runnable loop/output contract unverified | [github.com/WujiangXu/AEL](https://github.com/WujiangXu/AEL) (implementation) | [github.com/WujiangXu/AEL](https://github.com/WujiangXu/AEL) @ `c95f5f961667e7df4bdddf750b22332158951bf2` | MIT | `python experiments/run_portfolio.py --config experiments/configs/incremental/step3_tool_memory_reflect.yaml --dataset experiments/configs/dataset_d_full.yaml --seed 42` |
| aflow | Native engine candidate; runnable loop/output contract unverified | [github.com/FoundationAgents/AFlow](https://github.com/FoundationAgents/AFlow) (implementation) | [github.com/FoundationAgents/AFlow](https://github.com/FoundationAgents/AFlow) @ `3f457218fc716093fe53f6df8a5d5e6379d66346` | MIT | unknown |
| agentsquare | Native engine candidate; runnable loop/output contract unverified | [github.com/tsinghua-fib-lab/AgentSquare](https://github.com/tsinghua-fib-lab/AgentSquare) (implementation) | [github.com/tsinghua-fib-lab/AgentSquare](https://github.com/tsinghua-fib-lab/AgentSquare) @ `8f5b3fe5d8a32f9b59d20370823bef2a2c86928c` | unknown | `python agent_search.py`; cwd `search` |
| ahe | Native engine candidate; runnable loop/output contract unverified | [github.com/china-qijizhifeng/agentic-harness-engineering](https://github.com/china-qijizhifeng/agentic-harness-engineering) (implementation) | [github.com/china-qijizhifeng/agentic-harness-engineering](https://github.com/china-qijizhifeng/agentic-harness-engineering) @ `8b2a55d97590363fe50c3cc6b5e833b020a4bb4c` | MIT | `uv run python evolve.py --config configs/base.yaml` |
| evoflow | Native engine candidate; runnable loop/output contract unverified | [github.com/bingreeky/EvoFlow](https://github.com/bingreeky/EvoFlow) (implementation) | No immutable task-source pin captured | unknown | unknown |
| evoskill | Native engine candidate; runnable loop/output contract unverified | [github.com/sentient-agi/EvoSkill](https://github.com/sentient-agi/EvoSkill) (implementation) | [github.com/sentient-agi/EvoSkill](https://github.com/sentient-agi/EvoSkill) @ `36f6f04952293d7054145550c2b9f0b0411bff1c` | Apache-2.0 | unknown |
| g-del-agent | Native engine candidate; runnable loop/output contract unverified | [github.com/Arvid-pku/Godel_Agent](https://github.com/Arvid-pku/Godel_Agent) (implementation) | [github.com/Arvid-pku/Godel_Agent](https://github.com/Arvid-pku/Godel_Agent) @ `bbb508796be31c7140cdfc7106efd830a1324242` | MIT | `python src/main.py`; cwd `.` |
| hsi | Native engine candidate; runnable loop/output contract unverified | [github.com/TailinZhou/hsi](https://github.com/TailinZhou/hsi) (implementation) | [github.com/TailinZhou/hsi](https://github.com/TailinZhou/hsi) @ `97a022b9a9c260c0498806fc9826ebf22e753ed9` | unknown | unknown |
| hyperagents | Native engine candidate; runnable loop/output contract unverified | [github.com/facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents) (implementation) | [github.com/facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents) @ `59a68f672dfb92c74aeb7e61535d776fb36e172d` | CC-BY-NC-SA-4.0 | unknown |
| limen | Native engine candidate; runnable loop/output contract unverified | [github.com/Lossfunk/LIMEN](https://github.com/Lossfunk/LIMEN) (implementation) | [github.com/Lossfunk/LIMEN](https://github.com/Lossfunk/LIMEN) @ `cf0b44da37f7e7ee038920c860a8cb00c610c9af` | MIT | unknown |
| mce | Native engine candidate; runnable loop/output contract unverified | [github.com/metaevo-ai/meta-context-engineering](https://github.com/metaevo-ai/meta-context-engineering) (implementation) | [github.com/metaevo-ai/mce-artifact](https://github.com/metaevo-ai/mce-artifact) @ `c63300daef93404e22e2569b3d08e72843e7123b`<br>[github.com/metaevo-ai/meta-context-engineering](https://github.com/metaevo-ai/meta-context-engineering) @ `c4b7a7c2ce3ffc4bf4a74c52d2dd8a9a8fb14c30` | MIT<br>MIT | unknown<br>`bash scripts/train_symptom_diagnosis.sh`; cwd `.` |
| meta-ttl | Native engine candidate; runnable loop/output contract unverified | [github.com/zzzlou/meta-ttl](https://github.com/zzzlou/meta-ttl) (implementation) | [github.com/zzzlou/meta-ttl](https://github.com/zzzlou/meta-ttl) @ `b72db4b77e9ae01aec1cbfd36ae0edae902b6468` | unknown | unknown |
| omni-epic | Native engine candidate; runnable loop/output contract unverified | [github.com/maxencefaldor/omni-epic](https://github.com/maxencefaldor/omni-epic) (implementation); [dub.sh/omniepic](https://dub.sh/omniepic) (project) | [github.com/maxencefaldor/omni-epic](https://github.com/maxencefaldor/omni-epic) @ `af2a3c64f40bc48178c08e1beb76a0aafdd2a167` | Apache-2.0 | unknown |
| sica | Native engine candidate; runnable loop/output contract unverified | [github.com/MaximeRobeyns/self_improving_coding_agent](https://github.com/MaximeRobeyns/self_improving_coding_agent) (implementation) | [github.com/MaximeRobeyns/self_improving_coding_agent](https://github.com/MaximeRobeyns/self_improving_coding_agent) @ `ed8275dca4d3c5dbf77229964351fe9b424797dc` | MIT | unknown |

### Prompt-search implementation candidates

| Record | Integration identity / scope | Reviewed link | Task-source or Arena repository pin | Captured license | First captured command (not run) |
| --- | --- | --- | --- | --- | --- |
| evoprompt | Native engine candidate; runnable loop/output contract unverified | [github.com/beeevita/EvoPrompt](https://github.com/beeevita/EvoPrompt) (implementation) | [github.com/beeevita/EvoPrompt](https://github.com/beeevita/EvoPrompt) @ `94caff336555df99acc5c338c7930c40cc550ad9` | MIT | unknown |
| promptagent | Native engine candidate; runnable loop/output contract unverified | [github.com/XinyuanWangCS/PromptAgent](https://github.com/XinyuanWangCS/PromptAgent) (implementation) | [github.com/XinyuanWangCS/PromptAgent](https://github.com/XinyuanWangCS/PromptAgent) @ `2edfc9e4462a6af97dc973442d074de9b3e876b2` | Apache-2.0 | `python src/main.py --config_dir example_config.yaml` |
| sepo | Native engine candidate; runnable loop/output contract unverified | [github.com/taowangcheng/SePO](https://github.com/taowangcheng/SePO) (implementation) | [github.com/taowangcheng/SePO](https://github.com/taowangcheng/SePO) @ `83083782a9487ef61962d933fc72abbe95f9fa76` | unknown | unknown |

### Specialized or unresolved implementation candidates

| Record | Integration identity / scope | Reviewed link | Task-source or Arena repository pin | Captured license | First captured command (not run) |
| --- | --- | --- | --- | --- | --- |
| accelopt | Kernel optimization; hardware/runtime-specific adapter | [github.com/zhang677/AccelOpt](https://github.com/zhang677/AccelOpt) (implementation) | [github.com/zhang677/AccelOpt](https://github.com/zhang677/AccelOpt) @ `47e29a7c24704e3c3e534b5bcbf39cfac3f831e3` | Apache-2.0 | unknown |
| eob | Anonymous corpus implementation link; repository identity and immutable checkout need verification | [anonymous.4open.science/r/EoB](https://anonymous.4open.science/r/EoB) (implementation) | [github.com/MetaEvo/EoB](https://github.com/MetaEvo/EoB) @ `5d9f30cb19a0231a74f58d17926cff828db6857f` | unknown | unknown |
| evoor-agent | Anonymous corpus implementation link; repository identity and immutable checkout need verification | [anonymous.4open.science/r/pL8xY2mQ8rA5fC3vB7nK](https://anonymous.4open.science/r/pL8xY2mQ8rA5fC3vB7nK) (implementation) | [github.com/EvoNexusX/2026HuangEvoORAgent](https://github.com/EvoNexusX/2026HuangEvoORAgent) @ `1a255eaade3b325706ab9b2ad1e20f2aafae0a06` | unknown | unknown |
| ready | Anonymous corpus implementation link; repository identity and immutable checkout need verification | [anonymous.4open.science/r/ICML_READY-747F](https://anonymous.4open.science/r/ICML_READY-747F) (implementation) | No immutable task-source pin captured | unknown | unknown |
| revolve | Reward-learning/RL; environment-specific training adapter | [github.com/RishiHazra/Revolve/tree/main](https://github.com/RishiHazra/Revolve/tree/main) (implementation); [rishihazra.github.io/REvolve](https://rishihazra.github.io/REvolve) (project) | [github.com/RishiHazra/Revolve](https://github.com/RishiHazra/Revolve) @ `eee636b5dba141bf00cf0ff47852c2a9125dc5d2` | MIT | `python main.py environment.name=HumanoidEnv` |

## 12 project/artifact-only records

These are not automatically new standalone frameworks. They can point to a reusable underlying engine, a project page, or only released outputs. Task-source repository discovery is shown without upgrading participant status.

| Record | Integration identity / scope | Reviewed link | Task-source repository pin | Captured license | First captured command (not run) |
| --- | --- | --- | --- | --- | --- |
| alphaevolve | Results notebook only; no AlphaEvolve search implementation established | [colab.research.google.com/github/google-deepmind/alphaevolve_results/blob/master/mathematical_results.ipynb](https://colab.research.google.com/github/google-deepmind/alphaevolve_results/blob/master/mathematical_results.ipynb) (artifact) | [github.com/google-deepmind/alphaevolve_results](https://github.com/google-deepmind/alphaevolve_results) @ `4226acbf237ff9ad10ba7673a2af127a2d8a5971` | Apache-2.0 (software); CC-BY-4.0 (other material) | unknown |
| dreureka | Project page; discovered DrEureka repository needs revision-specific interface check | [eureka-research.github.io/dr-eureka](https://eureka-research.github.io/dr-eureka) (project) | [github.com/eureka-research/DrEureka](https://github.com/eureka-research/DrEureka) @ `1d4e00700423170717654516f4ef4b24cb0f3a84` | MIT | unknown |
| eureka | Project page; discovered Eureka repository has documented RL search command | [eureka-research.github.io](https://eureka-research.github.io) (project) | [github.com/eureka-research/Eureka](https://github.com/eureka-research/Eureka) @ `9eee42808b52d8abc14845d1547bfde886403ccc` | MIT | `python eureka.py env=cartpole` |
| lasr | Project page; Julia symbolic-regression implementation candidate | [trishullab.github.io/lasr-web](https://trishullab.github.io/lasr-web) (project) | [github.com/trishullab/LibraryAugmentedSymbolicRegression.jl](https://github.com/trishullab/LibraryAugmentedSymbolicRegression.jl) @ `776196e339191736e20d4eb6eed7c468aa6e4472` | Apache-2.0 | unknown |
| llamea-hpo | Replication artifact; LLaMEA framework is a separate underlying engine | [doi.org/10.5281/zenodo.13834123](https://doi.org/10.5281/zenodo.13834123) (artifact) | [github.com/XAI-liacs/LLaMEA](https://github.com/XAI-liacs/LLaMEA) @ `2a200f6b48038358223326b45869892b8ca09c4d` | MIT | unknown |
| llamea-mobo | Published selected algorithms; captured commands benchmark them, search loop not established | [github.com/glatq/LLaMEA-MOO/tree/publication_llamea_moo_unconstrained](https://github.com/glatq/LLaMEA-MOO/tree/publication_llamea_moo_unconstrained) (artifact) | [github.com/glatq/LLaMEA-MOO](https://github.com/glatq/LLaMEA-MOO) @ `18861aa47f17905c28aa33c5a9f33df3a893d191` | MIT | `python benchmark_best_codes.py config=conf/benchmark_phase1.yaml`; cwd `.` |
| llm-flowrepair | Replication archive; no source repository pin captured | [doi.org/10.5281/zenodo.21976165](https://doi.org/10.5281/zenodo.21976165) (artifact) | No immutable task-source pin captured | unknown | unknown |
| meta-harness | Released Terminal-Bench harness artifact, not the complete meta-search loop | [yoonholee.com/meta-harness/](https://yoonholee.com/meta-harness/) (project); [github.com/stanford-iris-lab/meta-harness-tbench2-artifact](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact) (artifact) | [github.com/stanford-iris-lab/meta-harness-tbench2-artifact](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact) @ `57fefdb2ff84af3fd81b69d67814acbe69bd0743` | unknown | `harbor run --agent-import-path agent:AgentHarness -d terminal-bench@2.0 -m anthropic/claude-opus-4-6 -e runloop -n 20 --n-attempts 5`; cwd `.` |
| mipro | DSPy optimizer component; not a separate standalone runtime | [dspy.ai](http://dspy.ai) (project) | [github.com/stanfordnlp/dspy](https://github.com/stanfordnlp/dspy) @ `40a6e168914a7b81a78b1a081d93f26de18c8d0d` | MIT | unknown |
| qdaif | OpenELM-based method plus scripts/data; distinguish framework from experiment | [qdaif.github.io/](https://qdaif.github.io/) (project) | [github.com/CarperAI/OpenELM](https://github.com/CarperAI/OpenELM) @ `c844e149e3f59fef546e0bc55f4e12e0f192feb9`<br>[github.com/qdaif/qdaif_scripts_data](https://github.com/qdaif/qdaif_scripts_data) @ `9836aaf1a7703fdafb9560bd7a304ac1df4572fd` | MIT<br>unknown | unknown<br>unknown |
| reevo | Project page; discovered ReEvo repository has documented native command | [ai4co.github.io/reevo](https://ai4co.github.io/reevo) (project) | [github.com/ai4co/reevo](https://github.com/ai4co/reevo) @ `6dce18257da5e11db2d138e417a2fffc5c72d05f` | MIT | `python main.py problem=tsp_gls` |
| text2reward | Project page; source commands train RL policies using reward code, generation loop unverified | [text-to-reward.github.io/](https://text-to-reward.github.io/) (project) | [github.com/xlang-ai/text2reward](https://github.com/xlang-ai/text2reward) @ `e7f57efcf76b22bbfb7c3eb9d67d98ff2765a926` | unknown | `python sac.py --env_id drawer-open-v2 --train_num 8 --eval_num 5 --eval_freq 16_000 --max_episode_steps 500 --train_max_steps 1_000_000 --seed 12345 --exp_name zero-shot --reward_path ./reward_code/drawer-open-v2/specific.py` |

## 39 records without a reviewed implementation/project/artifact link

A blank corpus code link is not proof that code does not exist. The 11 rows with task-source discoveries below need attribution verification before becoming execution registrations. The remaining 28 have no repository pin in either reviewed source used here.

| Record | Integration identity / scope | Reviewed link | Task-source repository pin | Captured license | First captured command (not run) |
| --- | --- | --- | --- | --- | --- |
| a2dept | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| ael | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| aevo | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| algoevolve | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| autorise | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/Tele-EVOL/TeleAI-Safety](https://github.com/Tele-EVOL/TeleAI-Safety) @ `ae8509926ae91fd36d68c5a252787b70b73e7d21` | unknown | unknown |
| avo | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| cae | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| cocoevo | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/lbaf23/llm-cocoevo](https://github.com/lbaf23/llm-cocoevo) @ `504355b568b2a0cbd4054783c80bac9c76a4de6d` | unknown | unknown |
| codeevolve-salesforce | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| constitutional-evolution | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| darwinian-evolver | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/imbue-ai/darwinian_evolver](https://github.com/imbue-ai/darwinian_evolver) @ `7f12365d2059c47e29068a5a6f498a293148d2a9` | AGPL-3.0 | unknown |
| deevo | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| dga2d | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| drsr | CoEvo source is shared/inherited provenance, not evidence of a distinct DrSR engine | No code/project/artifact link captured | [github.com/pgg3/CoEvo](https://github.com/pgg3/CoEvo) @ `dcad65e9799961cf67cf29865ff41dda2902a808` | MIT | unknown |
| elm | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| enpire | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/NVlabs/ENPIRE](https://github.com/NVlabs/ENPIRE) @ `99ee90acf65b5b18957c8382ad580db999528be3` | Apache-2.0 | unknown |
| eoh-s | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/FeiLiu36/EoH-S](https://github.com/FeiLiu36/EoH-S) @ `8310b056ab0d4ea83d194f1d9e8c7873c0a3b892` | MIT | unknown |
| evoprompting | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| flowscout | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| funbo | MetaBO is a baseline source, not a FunBO search implementation | No code/project/artifact link captured | [github.com/boschresearch/MetaBO](https://github.com/boschresearch/MetaBO) @ `3f458bd32db340fbe2d5f072a92cfd782072342c` | AGPL-3.0-or-later | unknown |
| funl2o | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| gaapo | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| gea | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/UCSB-AI/GEA](https://github.com/UCSB-AI/GEA) @ `d185edffd1f9fbd2297f4de8c6c9f94547448b6d` | Apache-2.0 | unknown |
| kernelpro | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| l-autoda | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/pgg3/L-AutoDA](https://github.com/pgg3/L-AutoDA) @ `f35ca7915c60425e884325f08e9203091c39da82` | unknown | unknown |
| llm-evolved-rl-algorithms | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/sygkounas/Designing-and-Evolving-New-Reinforcement-Learning-Algorithms-using-Large-Language-models](https://github.com/sygkounas/Designing-and-Evolving-New-Reinforcement-Learning-Algorithms-using-Large-Language-models) @ `b69c4edee1dd37a684c75a1c904190e9a66e1995` | unknown | unknown |
| llmastool | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| lmx | Later task-source repository discovery; corpus-to-implementation identity unverified | No code/project/artifact link captured | [github.com/jal278/lmx](https://github.com/jal278/lmx) @ `b8fec5dd16451cf7afb6e02ac621b71d5bdfee7f` | MIT | unknown |
| magellan | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| mind-evolution | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| pairwise-validator | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| pdr | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| phaseevo | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| polymath | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| promptbreeder | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| redahd | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| rqgm | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| satlution | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |
| stride | No implementation established in reviewed sources | No code/project/artifact link captured | No immutable task-source pin captured | unknown | unknown |

## Integration blockers and observer boundaries

- **Scope:** observing saved runs and launching a native framework are separate deliverables. Neither establishes canonical evaluation on all 959 tasks.
- **Identity:** preserve paper IDs while deduplicating shared engines; do not relabel a baseline, released solution, benchmark or example as the paper's executable framework.
- **Revision:** only three registrations exist. The other captured pins belong to task-source bibliography, not Arena's runnable registry. Current official documentation may differ from those pins.
- **Entrypoints:** most metadata does not identify the whole search loop; command hints sometimes run only evaluation (`Shinka evaluate.py`, LLaMEA-BO/MOO benchmark scripts) or a web app. Do not execute these as if they were uniform runners.
- **Outputs:** implement explicit revision-specific readers. Preserve native candidate identity, parent links, scores/directions, validity, evaluation budgets, timestamps, model usage, artifacts and unknown fields. Do not convert absent pause/resume support or telemetry into positive capability claims.
- **Environment:** credentials, optional models/embeddings, datasets, simulators, CUDA/IsaacGym, Docker and task evaluation dependencies need per-framework manifests. This inventory did not probe credentials or runtime readiness.
- **License:** unknown remains unknown. Captured AGPL entries (Darwinian Evolver, EurekAgent), Hyperagents' CC-BY-NC-SA-4.0, and artifact-specific terms need review against the exact distribution/integration plan; this is metadata, not a legal conclusion. CoEvo has inconsistent captured license metadata (`unknown` for CoEvo, `MIT` under DrSR referencing the same commit), so verify the actual license file rather than choosing the convenient value.

## Local clone / output evidence

The following local sources were inspected read-only; no installed framework package, live run credential, or executable was loaded. Worktree state is a point-in-time observation.

| Framework | Local checkout and origin | Local revision versus Arena registration | Local license evidence |
| --- | --- | --- | --- |
| SCiEL | `/Users/amoriodi/fall2026/sciel`; `git@github.com:Doldrums/sciel.git` | HEAD `9780950fab3842c01c6f2d4baacb12fe27061898`; registered `0d67f813dd4ac21dee304f2b0de0b0ce59bf4157` exists in the object store; 55 tracked working-tree differences | No tracked LICENSE/COPYING file or inspected project license declaration; unknown |
| AgenticOptimization | `/Users/amoriodi/fall2026/AgenticOptimization`; `https://github.com/Junye-Pan/AgenticOptimization.git` | HEAD `be17035a94ec5f45b17332ad612f7842989e805e`; no tracked differences; no Arena execution registration. The separate task-source pin `712b2fd4888c4b57fc08c1d2bdf4b1ca4c4517fb` was not used as this local HEAD | No tracked LICENSE/COPYING file or inspected project license declaration; unknown |
| ShinkaEvolve | `/tmp/sciel-shinka-integration.OizP77`; `https://github.com/SakanaAI/ShinkaEvolve.git` | HEAD exactly equals Arena pin `9912af12d423504b8d580f4179fd15f5f88b8c50`; no tracked differences | Apache-2.0 in [LICENSE](/tmp/sciel-shinka-integration.OizP77/LICENSE:1) |

No exact-name, case-insensitive DGM, ShinkaEvolve, OpenEvolve or skydiscover directories were found immediately under `/Users/amoriodi/fall2026` or `/tmp`. DGM's registered revision remains unverified locally, not proven unavailable elsewhere. The Shinka temporary directory is itself the actual clone. SCiEL worktree variants are not additional native frameworks.

### SCiEL native interfaces and output hints

The [CLI](/Users/amoriodi/fall2026/sciel/src/sciel/cli/main.py:163) declares `sciel run CONFIG --outputs DIR --run-id ID --tasks-root ROOT`, `sciel resume RUN_DIR`, dashboard and graceful-stop commands; its Python entry is `sciel.cli.main:main`. The [engine](/Users/amoriodi/fall2026/sciel/src/sciel/engine/loop.py:317) writes `sciel_events.jsonl` and `checkpoint.json`; CLI completion produces a JSON summary.

The separate [methods CLI](/Users/amoriodi/fall2026/sciel/src/sciel/methods/__main__.py:490) and [methods observer contract](/Users/amoriodi/fall2026/sciel/docs/methods-observer.md:3) use `python -m sciel.methods run --config CONFIG --output DIR` or `python -m sciel.diagnostics.methods_observer --config CONFIG --output DIR [--resume]`. Outputs include `run-config.json`, `resources.jsonl`, `provider-cost.json`, `registry/journal.jsonl`, dispatch receipts, `checkpoint.json`, `run-report.json`, `runtime.json` and per-invocation observations. The inspected methods config accepts only `sort` and `circle26`, requires an immutable Docker image and bounded accounting/config fields, and uses `OPENROUTER_API_KEY`. The methods config/CLI declarations also exist at the registered pin.

Blockers: choose general engine versus methods contract; use an isolated pinned checkout rather than the modified worktree; preserve the methods report's explicit incomplete infrastructure-cost coverage. Broader SCiEL framework features do not imply methods-task or Arena-runner coverage.

### ShinkaEvolve native interfaces and output hints, verified at the registered pin

[CLI documentation](/tmp/sciel-shinka-integration.OizP77/docs/cli_usage.md:45) exposes `shinka_launch` and `shinka_run --task-dir TASK --results_dir OUTPUT --num_generations N`; task directories contain `evaluate.py` and `initial.<ext>`. The [Python example](/tmp/sciel-shinka-integration.OizP77/README.md:113) uses `ShinkaEvolveRunner(...).run()`.

The pinned source writes **`programs.sqlite`**, [configured here](/tmp/sciel-shinka-integration.OizP77/shinka/core/async_runner.py:1192), plus [`prompts.sqlite`](/tmp/sciel-shinka-integration.OizP77/shinka/core/async_runner.py:1274), `evolution_run.log` and per-generation results. Older WebUI documentation still names `evolution_db.sqlite`; an observer must follow the actual source/config, not hardcode that stale example. [Database schema](/tmp/sciel-shinka-integration.OizP77/shinka/database/dbase.py:423) includes `programs`, `archive`, `metadata_store`, `generation_event_log` and `attempt_log`.

The [evaluator wrapper](/tmp/sciel-shinka-integration.OizP77/shinka/core/wrap_eval.py:89) expects `metrics.json` with maximizing `combined_score` and optional public/private metrics, plus `correct.json` containing `correct` and `error`. Native visualization is `shinka_visualize --db PATH`. A canonical evaluator bridge must handle task score direction and validity explicitly. Provider/embedding configuration and [pricing snapshot behavior](/tmp/sciel-shinka-integration.OizP77/README.md:163) remain setup concerns; the pin documents offline pricing mode.

### AgenticOptimization native interfaces and output hints

The [README](/Users/amoriodi/fall2026/AgenticOptimization/README.md:28) describes a persistent control plane launched by `PYTHONPATH=src python3 -m agentic_opt.web.app --state-root ao_state --db ao_state/control.sqlite3 --host 127.0.0.1 --port 5000`, followed by experiment creation and assignment start API calls. `codex-local` requires the Codex CLI; the [semantic worker](/Users/amoriodi/fall2026/AgenticOptimization/src/agentic_opt/adapter/semantic_worker.py:40) needs explicit assignment/session/API/workspace arguments.

SQLite owns semantic state; artifacts/logs/workspaces live under `ao_state`. [Control-plane routes](/Users/amoriodi/fall2026/AgenticOptimization/src/agentic_opt/web/routes_control_plane.py:57) expose evaluation, leaderboard and incumbent data; the [trace contract](/Users/amoriodi/fall2026/AgenticOptimization/docs/command_surface.md:245) defines immutable JSONL trace bundles with optional JSONL/OTLP exports. A task plugin implements `create_task()` / `TaskProtocol` with verify/probe/evaluate and candidate/runtime metadata.

Blockers: service/session lifecycle integration, absent Arena execution registration, unknown license declaration, and a [package metadata](/Users/amoriodi/fall2026/AgenticOptimization/pyproject.toml:9) README target (`docs/implementation_plan_codex.md`) that is missing in this checkout. No install was attempted to determine packaging readiness.

## Review completion

All 99 existing participant records appear exactly once in the three complete inventory sections (48 implementation-linked, 12 project/artifact-only, 39 without a captured link). The local check is deliberately bounded to named framework locations. Interfaces for the remaining implementations are unknown unless the table contains a recorded command or the direct-doc section explicitly establishes one. This report supports either observer or native-runner planning; the requested integration scope is still pending.
