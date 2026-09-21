# Agent, harness and workflow native recipes

This batch records 21 recipes for 20 corpus participants: 18 source-verified
implementation recipes, one frozen-agent evaluation artifact, and two explicit
blocks. MCE has separate primary-framework and artifact repository pins.
The 28 launch profiles preserve each implementation's own search loop and native
evaluation contract. None establishes canonical Arena task conformance or a
successful model-driven run. Source files were read and hashed; framework code,
model APIs, dataset installers and benchmark evaluators were not executed.

The machine-readable authority is
[`agent-systems.json`](../../registry/framework-recipes/agent-systems.json).
Every executable profile identifies its native entrypoint, working directory,
required files, evaluator evidence, allowed configuration overlays and native
artifact patterns. The shared driver verifies exact source evidence and stages
an isolated checkout before an explicit launch.

## Coverage

| Implementation | Exact source revision | Native interface and scope | License at inspected pin |
|---|---|---|---|
| ADAS | [2702bee8fefd](https://github.com/ShengranHu/ADAS/tree/2702bee8fefda42255efc5be9f60e3bd3db96ae4) | `arc`, `drop`, `mgsm`, `mmlu`, `gpqa` | Apache-2.0 |
| AEL-harness | [c95f5f961667](https://github.com/WujiangXu/AEL/tree/c95f5f961667e7df4bdddf750b22332158951bf2) | `portfolio` | MIT |
| AEvo | [87e2fefce6e9](https://github.com/FoundationAgents/Harnessing-Agentic-Evolution/tree/87e2fefce6e99922c736f0250060b082babd5578) | **Blocked:** Official Harnessing-Agentic-Evolution at the verified pin contains only README.md and LICENSE; no native code or entrypoint exists. The additional official FoundationAgents/AEvo repository returned no refs, including HEAD, on inspection. No optimizer can be connected from these placeholders. | MIT |
| AFlow | [3f457218fc71](https://github.com/FoundationAgents/AFlow/tree/3f457218fc716093fe53f6df8a5d5e6379d66346) | `workflow-search` | MIT |
| Agentic Optimization | [712b2fd4888c](https://github.com/Junye-Pan/AgenticOptimization/tree/712b2fd4888c4b57fc08c1d2bdf4b1ca4c4517fb) | `native-worker-search` | Unverified |
| AgentSquare | [8f5b3fe5d8a3](https://github.com/tsinghua-fib-lab/AgentSquare/tree/8f5b3fe5d8a32f9b59d20370823bef2a2c86928c) | `alfworld-search` | Unverified |
| AHE | [8b2a55d97590](https://github.com/china-qijizhifeng/agentic-harness-engineering/tree/8b2a55d97590363fe50c3cc6b5e833b020a4bb4c) | `harness-evolution` | MIT |
| Darwinian Evolver | [7f12365d2059](https://github.com/imbue-ai/darwinian_evolver/tree/7f12365d2059c47e29068a5a6f498a293148d2a9) | `parrot`, `circle-packing`, `multiplication-verifier` | AGPL-3.0 |
| EvoFlow | No verified pin | **Blocked:** The catalog provides no immutable implementation pin. The paper-cited https://github.com/bingreeky/EvoFlow.git returned Repository not found on the explicit fetch retry; no runnable adapter can be tied to verified source. | Unverified |
| EvoSkill | [36f6f0495229](https://github.com/sentient-agi/EvoSkill/tree/36f6f04952293d7054145550c2b9f0b0411bff1c) | `officeqa-skill-loop` | Apache-2.0 |
| Gödel Agent | [bbb508796be3](https://github.com/Arvid-pku/Godel_Agent/tree/bbb508796be31c7140cdfc7106efd830a1324242) | `mgsm-self-evolution` | MIT |
| GEA | [d185edffd1f9](https://github.com/UCSB-AI/GEA/tree/d185edffd1f9fbd2297f4de8c6c9f94547448b6d) | `swe-bench`, `polyglot` | Apache-2.0 |
| HSI | [97a022b9a9c2](https://github.com/TailinZhou/hsi/tree/97a022b9a9c260c0498806fc9826ebf22e753ed9) | `balrog-harness` | Unverified |
| HyperAgents | [59a68f672dfb](https://github.com/facebookresearch/Hyperagents/tree/59a68f672dfb92c74aeb7e61535d776fb36e172d) | `multi-domain` | CC-BY-NC-SA-4.0 |
| LIMEN | [cf0b44da37f7](https://github.com/Lossfunk/LIMEN/tree/cf0b44da37f7e7ee038920c860a8cb00c610c9af) | `rl-interface-search` | MIT |
| MCE | [c4b7a7c2ce3f](https://github.com/metaevo-ai/meta-context-engineering/tree/c4b7a7c2ce3ffc4bf4a74c52d2dd8a9a8fb14c30) | `skill-evolution` | MIT |
| MCE artifact profiles | [c63300daef93](https://github.com/metaevo-ai/mce-artifact/tree/c63300daef93404e22e2569b3d08e72843e7123b) | `skill-evolution`, `online-adaptation` | Unverified |
| Meta-Harness | [57fefdb2ff84](https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact/tree/57fefdb2ff84af3fd81b69d67814acbe69bd0743) | **Frozen artifact evaluation:** `terminal-bench-artifact` | Unverified |
| META-TTL | [b72db4b77e9a](https://github.com/zzzlou/meta-ttl/tree/b72db4b77e9ae01aec1cbfd36ae0edae902b6468) | `jericho`, `webarena` | Unverified |
| OMNI-EPIC | [af2a3c64f40b](https://github.com/maxencefaldor/omni-epic/tree/af2a3c64f40bc48178c08e1beb76a0aafdd2a167) | `open-ended-generation` | Apache-2.0 |
| SICA | [ed8275dca4d3](https://github.com/MaximeRobeyns/self_improving_coding_agent/tree/ed8275dca4d3c5dbf77229964351fe9b424797dc) | `self-improvement` | MIT |

AEvo was checked beyond the catalog: the official
`FoundationAgents/Harnessing-Agentic-Evolution` pin has only `README.md` and
`LICENSE`; `FoundationAgents/AEvo` advertised no refs or HEAD. EvoFlow's
paper-cited repository returned “Repository not found” on the targeted retry.
Neither placeholder is counted as a runnable framework.

## Explicit preparation and launch

Prepare a Python environment containing the selected native implementation's
dependencies first. Credentials belong in explicitly named environment variables,
not recipe JSON, argument values or configuration overlays. Arena does not
install packages, authenticate an agent CLI, prepare Docker images, acquire
benchmark data or check access to paid models while planning.

For example, an ADAS MGSM native spec has this shape:

```json
{
  "schema": "arena.native-run/1",
  "framework": "adas",
  "source_dir": "/absolute/ADAS-at-recipe-pin",
  "output_dir": "/absolute/new-adas-run",
  "timeout_seconds": 600,
  "environment_names": ["OPENAI_API_KEY"],
  "request": {
    "python": "/absolute/native-venv/bin/python",
    "profile": "mgsm",
    "arguments": ["--n_generation", "2", "--max_workers", "1"],
    "inputs": {},
    "config_overlays": {}
  }
}
```

`python -m arena.frameworks plan spec.json` validates and returns the concrete
command without importing the participant. `run spec.json` is the separate
execution operation. Native argument choices, datasets and models must match
the pinned parser. The outer timeout is a process bound, not a model-cost cap.

`inputs` maps new workspace-relative paths to absolute prepared files or folders.
`config_overlays` may replace only a profile's declared configuration paths;
their provenance is recorded. Do not embed credential values in either mapping.
The framework's source and Arena code are not mutable configuration overlays.
Native output flags fixed by the profile cannot be overridden by user arguments.

## Integration details and boundaries

- **ADAS:** five actual native search/evaluation scripts, with their original
  ARC, DROP, MGSM, MMLU and GPQA datasets and split behavior. Generated agents
  execute Python code under the upstream harness.
- **AFlow:** uses `run.py` and the real optimizer/evaluator. Stage the native
  `config/config2.yaml` from its pinned example with environment references.
- **AgentSquare:** launches the ALFWorld search in `search/`; native modules,
  models and iteration settings remain source-defined. Its exception handler
  can log failure and still exit zero, so process completion is insufficient
  evidence of a successful run.
- **AEL:** the actual pinned portfolio parser has no `--dataset` flag. The
  recipe uses its supported config/model/seed/episode interface. Existing
  backtest logs and paper-result JSON are baselines, not new evaluations.
- **AHE:** requires prepared NexAU/Harbor/E2B infrastructure and a dataset-aware
  config. Disable optional webhook notifications unless separately authorized.
- **Darwinian Evolver:** three released registry problems retain the actual
  organism/mutator/evaluator loop. Pickle snapshots are never deserialized by
  Arena; ARC-specific experiments are not implied by these profiles.
- **EvoSkill:** a small runtime-only bridge invokes the exact console function
  declared by its `pyproject.toml`. The OfficeQA project must have prepared data,
  an explicitly configured execution mode and the selected agent CLI.
- **GEA and HyperAgents:** run the native multi-agent/agent-code evolution
  loops. Prepared Docker/domain harnesses remain required; upstream initial
  scores and copied agents are not independent measurements.
- **HSI:** the tracked `.env` is removed only from the isolated execution
  checkout, without reading or hashing its contents. Supply the model key
  through explicit environment names. Native BALROG games/harnesses need setup.
- **LIMEN and OMNI-EPIC:** preserve native RL/simulator/GPU evaluation. Different
  environment returns do not acquire a common Arena fitness merely by importing
  their logs. Hydra/config output settings must stay inside the run workspace.
- **MCE:** both pinned repositories expose actual evolution loops; the artifact
  additionally exposes online adaptation. Online learning on a test stream is
  explicitly distinguished from untouched held-out evaluation.
- **META-TTL:** the public pin contains Jericho and WebArena meta-training.
  Fixed models/settings and native train/validation behavior remain intact;
  no tau2-bench implementation is inferred from the paper's broader task list.
- **SICA:** the ordinary runner executes native self-improvement. Its `test`
  subcommand is a benchmark-only operation, not a substitute for that loop.
- **Meta-Harness:** the repository provides the frozen `AgentHarness` evaluated
  through Harbor, not the process that discovered it. The bridge resolves the
  installed Harbor console entrypoint; that dependency version is not pinned
  by this repository and needs separate environment validation.

### Gödel Agent credential-file bridge

The pinned `src/agent_module.py` instantiates an agent during import and directly
reads `src/key.env`. The driver therefore creates that one file exclusively with
mode `0600` from inherited `OPENAI_API_KEY`, invokes native `src/main.py`
unchanged, and removes the file after normal completion, Python exceptions,
SIGINT or SIGTERM. It refuses to overwrite an existing path. No credential
content is included in the plan, file evidence, recipe or result patterns.
SIGKILL or host failure can prevent cleanup: run this profile only in a private,
disposable workspace and remove that workspace if the process is killed abruptly.
The native released loop is MGSM-specific; it does not imply every paper task.

### AgenticOptimization native control bridge

The driver follows the pinned README's real control API: it creates a loopback
service on an ephemeral port, creates one budgeted `codex-local` experiment and
assignment, starts that assignment, and lets native `WorkerManager` own search,
continuation and evaluation. It does not substitute a web server for optimization.
The required arguments are `--task-id`, `--max-evaluator-runs`, `--worker-seconds`
and `--wall-seconds`; `--codex-binary` optionally selects an absolute native CLI.
Arena fixes `--state-root` to the run output. The selected native task package,
Codex authentication and task runtime must already be available.

On exit or wall timeout the driver requests native experiment stop and invokes
native worker cleanup before closing the service. The native control database,
worker logs and a small `arena-native.json` termination record are preserved.
A terminal process does not establish scientific validity; missing terminal
session evidence is not treated as successful completion. The source pin has
no verified root license or dependency manifest.

## Verification

`python -m pytest tests/frameworks/test_agent_recipes.py -q` checks complete
coverage, source hashes when the exact local checkouts are available, all 28
inert preparation profiles, protected outputs, native API payloads, timeout
cleanup and private temporary-credential handling. The fixtures do not invoke
paid models, native search code, Docker workloads or benchmark evaluation.
