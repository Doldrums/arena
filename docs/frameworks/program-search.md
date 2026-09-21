# Program-search implementation profiles

This batch registers 19 research records: 17 source-verified native launch profiles and two explicitly blocked integrations. Source verification means that the command, native evaluator, configuration and file hashes were inspected at immutable Git revisions. It does not mean dependencies were installed, a provider call succeeded, or an end-to-end research run passed conformance. No native imports, experiments or paid calls were used to construct this batch.

The recipes are in [`program-search.json`](../../registry/framework-recipes/program-search.json). Each profile preserves the framework’s native loop and task evaluation. The generic adapter launches in an isolated source copy and inventories native artifacts. It does not infer a common score, validity, canonical evaluation, cost total or compatibility with every Arena task.

| Research record | Native integration and scope | Pinned implementation evidence |
|---|---|---|
| AdaEvolve | Native SkyDiscover optimization calls the pinned circle-packing evaluator and records its native metrics. | [`0d932b69`](https://github.com/skydiscover-ai/skydiscover/blob/0d932b690670a7e544388ad362e9876c8bd256a0/skydiscover/optimize/cli.py#L116) |
| BaSE | Native BaSE live greedy arms call the task evaluator and save per-arm results and allocation trace. | [`ae7b5da1`](https://github.com/keruiwu/self-evolving-allocation/blob/ae7b5da1db39c0fd826adda7893c99d5bda5ac1b/run_base.py#L68) |
| CodeEvolve | Native CodeEvolve islands invoke evaluate.py with program and JSON-result paths; metrics include benchmark_ratio and eval_time. | [`c077959e`](https://github.com/inter-co/science-codeevolve/blob/c077959e1ab24b060aaa6d4c563bca2e9cbe8617/src/codeevolve/cli.py#L90) |
| CoEvo | Native CoEvoMethod.run searches its multi-representation solution chains and invokes Oscillation1Task evaluation. | [`dcad65e9`](https://github.com/pgg3/CoEvo/blob/dcad65e9799961cf67cf29865ff41dda2902a808/main_run.py#L1) |
| CORAL | CORAL runs its native agent manager in the foreground and grades attempts through the configured circle-packing Grader. | [`0123dfb9`](https://github.com/Human-Agent-Society/CORAL/blob/0123dfb939b35228cf2c1fde224cd0561e727408/coral/cli/start.py#L1) |
| Deliberate Evolution | The pinned repository contains only README.md and states that code, benchmarks and reproduction instructions will be added later. No implementation entrypoint is available. | [`18ae1f1c`](https://github.com/Xinyu-Pang/Deliberate-Evolution/blob/18ae1f1c33a0dfa3c81298bba035036d3b23ecaf/README.md#L9) |
| EoH | Native EoH.run uses BPONLINE.evaluate_program; the driver only supplies parameters and environment credentials. | [`47254578`](https://github.com/FeiLiu36/EoH/blob/472545785c936dcfc863d2bc0d6109cf23c7ce62/eoh/src/eoh/run.py#L13) |
| EurekAgent | The native research pipeline uses the private grader grade_submission and is_better contract in a separate Docker grader. | [`fb96df89`](https://github.com/THU-Team-Eureka/EurekAgent/blob/fb96df897dfb99797a77623aa0dd9ee178fe89d2/src/__main__.py#L49) |
| EvolCAF | Authentic historical EvolCAF evolves cost-aware acquisition functions through eoh.EVOL and Evaluation.evaluate; the native objective is mean BO optimality gap (lower is better). | [`4b2338fc`](https://github.com/FeiLiu36/EoH/blob/4b2338fc2317c743cec50c5c7a2e4684707af973/examples/user_bo_caf/runEoH.py#L1) |
| EvoX | Native SkyDiscover optimization calls the pinned circle-packing evaluator and records its native metrics. | [`0d932b69`](https://github.com/skydiscover-ai/skydiscover/blob/0d932b690670a7e544388ad362e9876c8bd256a0/skydiscover/optimize/cli.py#L116) |
| FunSearch re-implementation | The kitft re-implementation runs its own async FunSearch samplers and sandbox evaluator on a cap-set specification. | [`cec37d84`](https://github.com/kitft/funsearch/blob/cec37d84b474ea6bbd66f6defad8f5b5758449ff/funsearch/__main__.py#L57) |
| HSEvo | Native heuristic evolution invokes problems/bpp_online/eval.py for training and the native validation pass. | [`f3afffab`](https://github.com/datphamvn/HSEvo/blob/f3afffabc2b458fddf70a42a8678758039671297/main.py#L15) |
| LLM-LEx | Native llmlex.run_genetic proposes and fits expressions; returned populations retain native negative normalized chi-squared scores. | [`9f02b58c`](https://github.com/harveyThomas4692/llmlex/blob/9f02b58c5efb6d3c973c2ad2552ecc3a57998f81/llmlex/llmlex.py#L515) |
| LoongFlow | Native MathPESAgent executes its planner/executor/summary loop and evaluates generated programs with the pinned math task. | [`945c78bc`](https://github.com/baidu-baige/LoongFlow/blob/945c78bc1554f8281aac40320b3599bd68d528d7/agents/math_agent/math_evolve_agent.py#L1) |
| MCTS-AHD | Native heuristic evolution invokes problems/bpp_online/eval.py for training and the native validation pass. | [`ee9c4f42`](https://github.com/zz1358m/MCTS-AHD-master/blob/ee9c4f424503c65a5fd2b899e6620ce86079fedb/main.py#L12) |
| MEoH | Native MEoH.run preserves the two-objective OBP evaluator: negative mean bin count and negative evaluation time. | [`ffb6acf6`](https://github.com/Optima-CityU/LLM4AD/blob/ffb6acf64497be93932c98d25369352efd3865cf/llm4ad/method/meoh/meoh.py#L45) |
| RankEvolve | Native RankEvolve uses its configured BM25 evaluator and stores run.db, trace.jsonl and experiment summaries. | [`8f664bcd`](https://github.com/fangchenli/ranking-evolved/blob/8f664bcd5123bac2397f0c1bfbdb347ca3233483/src/ranking_evolved/cli.py#L45) |
| ReEvo | Native heuristic evolution invokes problems/bpp_online/eval.py for training and the native validation pass. | [`6dce1825`](https://github.com/ai4co/reevo/blob/6dce18257da5e11db2d138e417a2fffc5c72d05f/main.py#L12) |
| The Station | The native init/start path provisions station_data and starts a persistent multi-service deployment with daemonized servers. A managed deployment/stop/collect adapter is required; treating the launcher exit as bounded search completion would be incorrect. | [`782088e5`](https://github.com/dualverse-ai/station/blob/782088e561998bf357d95a838a0566a8229425d9/start.sh#L294) |

## Using a profile

Install the selected native environment separately at the recipe revision. Supply an absolute interpreter from that environment, explicit native arguments, a fresh output path and a wall-time bound. Planning reads metadata and hashes only:

```json
{
  "schema": "arena.native-run/1",
  "framework": "eoh",
  "source_dir": "/absolute/pinned-eoh-checkout",
  "output_dir": "/absolute/new-run",
  "timeout_seconds": 1800,
  "environment_names": ["OPENAI_API_KEY"],
  "request": {
    "python": "/absolute/eoh-env/bin/python",
    "profile": "online-bin-packing",
    "arguments": ["--endpoint", "api.openai.com", "--model", "your-model",
                  "--population", "4", "--generations", "2", "--samples", "8"]
  }
}
```

`python -m arena.frameworks plan spec.json` validates the request without executing the framework. `python -m arena.frameworks run spec.json` explicitly launches the native search and can spend provider/compute resources. `results` reads saved artifacts without running candidate code. The board itself never launches these commands.

`request.inputs` maps a new relative workspace destination to an existing absolute data path. `request.config_overlays` maps only declared native configuration files to reviewed, secret-free configurations. Inputs are hashed by the run planner. Provider credentials belong in explicitly allowed environment variables, never arguments, manifests or configuration snapshots. Recipe-fixed algorithm/task options and output destinations are protected from argument overrides.

## Library-only entrypoints

Four small reviewed drivers expose existing native APIs. Imports happen only inside explicit `main` execution; preparation and result reading do not import those libraries.

- EoH calls `EoH(...).run()` with the native `BPONLINE` problem. The driver accepts endpoint/model, population, generations, sample bound and worker counts.
- EvolCAF calls the historical `Paras.set_paras(...)` and `eoh.EVOL(...).run()` with the authentic `examples/user_bo_caf/prob.py` evaluator. No new optimizer is supplied.
- MEoH calls `MEoH(...).run()` with `OBP_2O_Evaluation` and the native profiler. Both native objectives are preserved: negative mean bins and negative evaluation time. It accepts host/model, population, generations, sample bound and worker counts.
- LLM-LEx calls `llmlex.run_genetic(...)`. Supply `--data inputs/data.json` through `request.inputs`, containing equally sized finite numeric `x` and `y` arrays. The native populations, formula strings, parameters and signed scores are saved as JSON; nonfinite values are explicit markers. Formula strings are never executed by artifact readers. This profile adds no held-out evaluation.

## Revision and environment details

**EvolCAF:** the task corpus records EoH `472545785c936dcfc863d2bc0d6109cf23c7ce62`, where its paper-linked example is absent. Git history identifies removal in `a8861e55a8e97adb9fc66a1fbc3cf154e34c1a0d`. The integration deliberately pins its parent, `4b2338fc2317c743cec50c5c7a2e4684707af973`, where the example README explicitly cites the EvolCAF paper. This recipe pin does not rewrite the original corpus provenance. It requires BoTorch 0.9.2. The pinned problem pickle is only loaded by native code during an explicit run; planning only hashes it. The native inner evaluator fixes ten trials and twenty joblib workers, independently of the driver’s outer worker count.

**CoEvo:** upstream prioritizes committed `model_config.json` over environment variables. Its evidence-hashed placeholder is removed from the isolated workspace so unchanged `main_run.py` takes `API_URL`, `API_KEY`, `MODEL` and optional `API_TIMEOUT` from the explicit environment. The source checkout stays unchanged. The external evotoolkit dependency and GPT-2 tokenizer cache must be prepared.

**ReEvo, HSEvo and MCTS-AHD:** native loops overwrite `problems/<task>/gpt.py` and invoke `python` subprocesses. They require the isolated workspace and the selected interpreter directory first in `PATH`. MCTS-AHD’s credential template needs a secret-free YAML overlay using native Hydra environment interpolation.

**CodeEvolve and LoongFlow:** native example configurations contain model or endpoint placeholders. Replace them through declared secret-free overlays. CodeEvolve requires Python >=3.13.5; LoongFlow requires >=3.12. LoongFlow passes its configured API key to LiteLLM; use a provider configuration that reads credentials from the explicit environment.

**CORAL and EurekAgent:** their native coding-agent tooling and nested container/grader environments must be prepared. CORAL is fixed to foreground `run.session=local`; native setup commands may still run during an explicitly launched search. EurekAgent requires lifecycle supervision of native Docker and agent subprocesses. Neither profile asserts that a parent process exit proves all descendants stopped.

**RankEvolve:** retrieval datasets, Java/Lucene and system resources are task prerequisites. The registered historical repository pin is retained even though its README points to a newer repository. Committed historical output is not evidence of a new Arena run.

Root licenses are recorded from pinned files. LLM-LEx has no root license file at this revision. LLM4AD’s root BSD-2-Clause license and MEoH module research-use notices are both reported without resolving their discrepancy.

## Remaining implementation gaps

Deliberate Evolution publishes an announcement only at the reviewed pin. The Station publishes a real implementation, but its supported startup path provisions and daemonizes a persistent multi-service deployment. It needs a managed initialize/start/stop/collect adapter before a bounded native launch can be claimed. These are specific integration gaps, not claims that either paper lacks scientific value.

Offline tests validate complete record coverage, fixed algorithm identity, source-tamper rejection, isolated/inert preparation, driver delegation and preservation of native scores and formula strings. They do not certify runtime performance or reproduce paper results.
