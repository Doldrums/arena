# Specialized native frameworks

The recipes in `registry/framework-recipes/specialized.json` cover the prompt,
ML, robotics and accelerator implementations listed below. Each repository is
pinned to an immutable commit from the task catalog. Source files supporting the
entrypoint and native evaluation carry SHA-256 hashes. These are **source-verified
launch integrations**, not reproduced paper results or built execution environments.
No model calls, training, package installation or framework import was used to
verify this batch.

A native run retains each method's optimizer and evaluation loop. Its artifacts
are recorded with `canonical_evaluation: false`; a native accuracy, hypervolume,
RL return, attack distance or model-feedback score is not silently converted to
an Arena task score. Generated candidates can use the separate Arena evaluation
contract only when their task interface actually matches it.

## Coverage

| Recipe | Exposed method or artifact | Execution boundary |
| --- | --- | --- |
| `gepa` | Native `gepa.optimize` API | Explicit factory supplies seed, data and native adapter/evaluator; metric-call budget required. |
| `gepa-artifact` | Original experiment reproduction artifact | Separate from the library; modified DSPy/Arbor dependencies and experiment configurations are not inferred from a command generator. |
| `mipro` | **DSPy MIPROv2** `compile` | This is the pinned component's actual name. Original MIPRO 2024 benchmark reproduction is not claimed. |
| `evoprompt` | Native GA/DE loop for classification, simplification and summarization | In-memory environment credential bridge; BBH is excluded because its parser registers `--content` twice. |
| `promptagent` | Native MCTS/beam search | Config supplies data and budgets; credential injection and logging redaction do not replace native search or evaluation. |
| `protegi` | Native textual-gradient search | In-memory `config.OPENAI_KEY` bridge; historical model names and unbounded request retries remain upstream limitations. |
| `sepo` | Awaiting source release | Pinned tree contains README/assets and says code release preparation is in progress. |
| `accelopt` | Complete native NKIBench/Trainium loop | One initial pass plus bounded feedback iterations, retaining planner, executor, experience selection and native hardware profiling. Prepared endpoints/Logfire/Neuron environment required. |
| `revolve` | Native reward evolution | `ROOT_PATH` points to the isolated clone; policy training and simulator feedback remain native. |
| `text2reward` | Reward-code generation and separate SAC evaluation | Generation alone produces code. Policy success requires an explicit simulator training/evaluation run. |
| `eureka` | Native generation → policy training → feedback → final evaluation | Isaac Gym/GPU environment needed; generated task source is written only into the clone. |
| `llamea-bo` | Native `run_exp` / `run_evolutions` | Credentials are passed directly from environment to the function, bypassing the CLI's key print. Native BBOB configuration is fixed by upstream. |
| `llamea-mobo` | Native multiobjective search | `mode=mo` is fixed; retain native feasibility/multiobjective metrics. Keep configuration API keys null. |
| `llamea-hpo` | Native LLaMEA with an explicit HPO evaluator factory | `HPO=True` requests configuration spaces; the evaluator supplied by the factory must actually perform inner HPO. |
| `llm-flowrepair` | No verified implementation repository | No executable method is attributed from unrelated benchmark code. |
| `qdaif` | OpenELM's QDAIF poetry environment and MAP-Elites loop | Native quality/genre/tone model feedback; not all paper domains are claimed. |
| `qdaif-artifact` | Companion analysis scripts and externally hosted results | Not a single verified end-to-end optimizer entrypoint. |
| `enpire` | Hardware-free reset/execute/verify harness example | Explicitly an artifact/harness profile. Physical tasks and autonomous research require configured station/services and fixed reset/reward rules. |
| `eoh-s` | Native EoHS whole-set evolution | Factory supplies a native set evaluator and LLM; no substitution with a single-program optimizer. |
| `l-autoda` | EvoToolkit-backed native attack evolution | Current pinned main, not the original standalone v1 artifact. RobustBench/PyTorch datasets/models required. |
| `llm-evolved-rl-algorithms` | Native evolution of complete RL update rules | Pinned code uses five environments, **two seeds**, one million training steps; README says five seeds. Neither description is silently substituted for the other. |
| `lmx` | Native symbolic-regression crossover/population loop | Explicit PMLB data and model weights; CSV history is an opaque artifact. |
| `cocoevo` | Native program/test co-evolution | Separate contest data and model endpoint required; private-test submission remains a separate upstream workflow. |
| `autorise` | Linked TeleAI-Safety benchmark only | The link does not establish an AutoRISE optimizer implementation. |

## Request contract

Use the shared `arena.native-run/1` specification. `source_dir` must be a clean
checkout of the exact recipe commit; `output_dir` must be new. The runtime clones
that source into `output_dir/workspace/<recipe-id>`, stages declared inputs and
runs the selected profile only on an explicit native-run invocation.

```json
{
  "schema": "arena.native-run/1",
  "framework": "gepa",
  "source_dir": "/absolute/gepa-checkout",
  "output_dir": "/absolute/new-run",
  "timeout_seconds": 3600,
  "environment_names": ["OPENAI_API_KEY"],
  "request": {
    "python": "/absolute/prepared-environment/bin/python",
    "profile": "native-api",
    "arguments": ["--factory", "inputs/factory.py:build", "--max-metric-calls", "100"],
    "inputs": {
      "inputs/factory.py": "/absolute/research/factory.py",
      "inputs/train.jsonl": "/absolute/research/train.jsonl"
    }
  }
}
```

All factory code, datasets and other external configuration must be declared in
`request.inputs` or `request.config_overlays`, so the runtime fingerprints them.
An input cannot overwrite tracked source. A configuration overlay can replace
only the configuration paths declared by that profile; evaluator source is not
an overlay. Factories are executable, trusted research code and are imported
**only during explicit execution**, never by metadata loading or planning.
Do not put credentials into argument vectors or configuration files. Select
credential environment names explicitly. Dependency/model caches and native
services are not installed or launched by planning.

Output flags are reserved by the profile and appended as absolute paths inside
the run output. Methods with hardcoded relative outputs write into their isolated
clone. Native result readers hash bounded artifacts; they do not import generated
code, load pickles or infer fitness from arbitrary logs/CSV/NumPy files.

## Factory interfaces

The `build()` function accepts no arguments and returns native objects. It may
read staged data and create model clients from the explicitly passed environment.
It must preserve the intended task split and evaluation protocol.

- **GEPA:** return the native `optimize` keyword arguments, including
  `seed_candidate`, `trainset`, and an `adapter` or evaluator/model configuration.
  The driver forces `max_metric_calls` and the output directory, disables optional
  WandB/MLflow and cloudpickle serialization, invokes `gepa.optimize` once, and
  saves the native `GEPAResult.to_dict()` payload. Native binary state remains
  unread by Arena.
- **MIPROv2:** return `{"optimizer": {...}, "compile": {...}}`. The first mapping
  contains `metric` and native model settings; the second contains `student`,
  `trainset` and the intended `valset`. The driver fixes `auto=None`, explicit
  `--candidates` and `--trials`, calls `MIPROv2(...).compile(...)`, then saves the
  compiled program as JSON with `save_program=False`.
- **EoH-S:** return `{"llm": native_llm, "evaluation": native_set_evaluator}`.
  Supply `--max-samples`, `--generations`, `--population` and `--workers`.
  The driver constructs native `EoHS` and `EoHSProfiler`, then runs the full loop.
  Released OBP/CVRP/TSP set-task examples show the native dataset contract.
- **LLaMEA-HPO:** return native constructor arguments including `f` (the actual
  inner-HPO evaluation callback) and `llm`. The driver forces `HPO=True`, logging,
  and `--generations`, then calls native `LLaMEA.run()`. The released HPO example
  is a reference for its SMAC/BBOB evaluator; the current example passes a stale
  `mutation_prompts` argument absent from the pinned constructor and is therefore
  not exposed as a runnable script.

## Credentials and native limitations

PromptAgent's upstream CLI and `BaseAgent.log_vars` print full model settings.
The bridge requires null API-key fields, injects `PROMPTAGENT_BASE_API_KEY` and
`PROMPTAGENT_OPTIM_API_KEY` (falling back to `OPENAI_API_KEY`) in memory, and redacts
only those fields while keeping native task/search/world-model construction.

EvoPrompt reads authentication from YAML. Its bridge replaces API-key fields in
an in-memory copy using `OPENAI_API_KEY`; it never writes the key to `auth.yaml`.
ProTeGi receives a transient `config` module with `OPENAI_KEY` from the environment.
LLaMEA-BO receives `GEMINI_API_KEY` through its function call. LLaMEA-MOBO logs its
configured key, so leave that field null and use native provider environment or
Vertex credentials instead.

Eureka's default `gpt-4-0314`, LLaMEA-BO's fixed Gemini model and ProTeGi's historical
models require compatible execution environments/endpoints. The integrations do
not assert that a provider still serves them. LMX's actual generator is hardcoded
to Galactica despite its alternate model flag; its independently standardized
held-out labels are another native protocol caveat. These findings are retained
rather than silently changing published algorithms or metrics.

Several native frameworks execute generated code or spawn simulator/training
processes. An outer host timeout is not an adversarial sandbox and does not
promise cancellation of remote services or independently launched Docker jobs.
Use the separately provisioned worker boundary for such runs. Available code and
source validation do not imply access-key issuance or paid-run authorization.

## Verification

`tests/frameworks/test_specialized_recipes.py` verifies inventory completeness,
artifact/version distinctions, inert driver imports, exact delegation to native
API contracts, budgets, credential handling and staged factory containment using
controlled fake native modules. No fake optimizer is exposed as a production
method: production drivers call the pinned upstream optimizers.

For the optional source-only conformance pass:

```sh
ARENA_SPECIALIZED_SOURCE_ROOT=/path/to/pinned-checkouts \
  python -m pytest -q tests/frameworks/test_specialized_recipes.py
```

Source directories are named after recipe IDs, except `gepa` uses `gepa-library`
and `gepa-artifact` uses `gepa`. The pass verifies every pin and evidence hash,
without installing dependencies or importing native source. Unknown/missing
licenses remain unknown; EoH-S includes additional research/commercial-use text
in source headers despite its MIT license file, so upstream terms need review.

## AccelOpt complete native loop

The `nkibench-complete-loop` profile runs the released Trainium pipeline for one
service. Its native sequence is initial experience construction, planning and
execution, then repeated previous-result staging, rewrite selection, candidate
selection, hardware profiling, experience construction, planning and execution.
The native kernel correctness checker and latency profiler are unchanged.

The upstream `experiments/full_complete_local/create_folders.py` substitutes
`$1` through `$15` in the native shell template before execution. Arena performs
a narrower equivalent preparation: it verifies the exact template hash, copies
it to the reserved output, and changes only `$10`…`$15` assignments to braced
`${10}`…`${15}` positional parameters. Every native stage command remains in
the copied script. `arena-patch.json` records the original and execution-copy
hashes, the six changes, baseline/config hashes and explicit iteration count.
The pinned original source is not modified.

Stage a prepared directory through `request.inputs`, for example:

```json
{
  "profile": "nkibench-complete-loop",
  "arguments": [
    "--prepared-dir", "inputs/accelopt",
    "--project", "research-project", "--organization", "research-org",
    "--iterations", "2", "--neuron-core", "0"
  ],
  "inputs": {"inputs/accelopt": "/absolute/prepared-accelopt-service"}
}
```

This is the recipe-specific part of a native request; also supply the prepared
Python interpreter and outer timeout in the shared specification. The bundle
contains `configs/planner_config.json`, `executor_config.json`,
`summarizer_config.json` (all three inside `configs/`), and a genuine native
`profile_results.csv` for exactly one service. The CSV requires `service_name`,
`task`, `kernel`, `profile`, `problem`, `values` and `case_name`. Task/kernel paths
refer to files inside the cloned workspace, including explicitly staged inputs.
The bridge rewrites only those paths to their relocated absolute locations.
Baseline values are preserved, not generated or certified by Arena.

Native model configs require `url`, `model`, and a nonsecret placeholder
`api_key` string (`None`, `EMPTY`, or `not-needed`). Provision a local or
worker-authenticated model endpoint. Service credentials are provided through
the explicitly selected environment. The worker needs AWS Trainium/Neuron, the
native kernel profiler, Logfire CLI/account/project and native dependencies;
planning does not install or probe them. The profile covers NKIBench, not the
separate NVIDIA/FlashInfer variants.

`--iterations` counts feedback passes **after one initial pass**. The driver
checks that all expected execution stages produced their native result files,
because upstream shell scripts do not consistently fail fast. Reused
minute-resolution iteration directories are rejected as incomplete evidence.
No candidate metric is inferred from shell exit status. An outer timeout still
bounds the worker process group; external model/profiling services remain
independent.
