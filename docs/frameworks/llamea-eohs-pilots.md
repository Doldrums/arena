# LLaMEA / LLaMEA-HPO and EoH-S CPU pilots

These are three native profiles from **two pinned implementations**, prepared
for seven exact local gateway model IDs. Ordinary LLaMEA and LLaMEA-HPO both
use XAI-liacs/LLaMEA at `2a200f6b48038358223326b45869892b8ca09c4d`, registered
under `llamea-hpo`. They are not the separately registered LLaMEA-BO system.
EoH-S uses FeiLiu36/EoH-S at `8310b056ab0d4ea83d194f1d9e8c7873c0a3b892`.

| Profile | Native search and evaluator | Pilot budget |
| --- | --- | --- |
| `llamea-hpo/gateway-bbob-pilot` | Native LLaMEA, unchanged packaged BBOB evaluator and AOCC helpers | 1 parent, 1 offspring, native run-history budget 4; 24 functions × 3 instances × 3 repetitions, dimension 5, 1,000 objective calls |
| `llamea-hpo/gateway-bbob-hpo-pilot` | Native LLaMEA with HPO enabled; packaged BBOB evaluator calls actual SMAC `AlgorithmConfigurationFacade.optimize`, then validates the incumbent | Same outer budget and final BBOB coverage; 8 SMAC trials per configuration-bearing candidate, 1,000 objective calls per BBOB run |
| `eoh-s/gateway-obp-set-pilot` | Native EoHS complementary search/population management, `OBPSEvaluation(return_list=True)` and packaged training pickle | Population 2, at most 8 registered samples / 4 generations; 1 sampler and 1 evaluator |

The HPO driver extracts the source example's imports, evaluator and prompts
after verifying the exact file SHA-256. It does not execute the example's
Gemini-specific main loop or pass its obsolete `mutation_prompts` argument.
Three recorded adjustments apply to that extracted evaluator: replace obsolete
`solution.keys()` with the current `solution.configspace is None` check; use
string SMAC instance IDs matching the native feature dictionary; reduce the
pilot's SMAC trials from 2,000 to 8 and objective budget from 10,000 to 1,000.
AOCC, SMAC's facade, incumbent validation, native mutation and selection remain
upstream code. Missing/unparseable configuration spaces retain the example's
explicit default-configuration fallback; HPO is not claimed for that candidate.
These budgets do not reproduce the paper's full protocol.

The ordinary BBOB evaluator is unchanged. The repository's `minimum_example.py`
is deliberately not used: it returns random fitness. The EoH-S pilot retains
the supplied training split with 128 instances. Its native default
`n_instances=32` stops at `n > n_instances`, so evaluation can use 33 entries;
the integration preserves and records that behavior instead of silently fixing
the scorer. Scores remain vectors for the set method, not an Arena scalar.
LLM4AD file headers require research-use acknowledgement/citation and direct
commercial-license inquiries to the authors. No private/licensed benchmark
download is needed for these packaged pilot tasks.

## Provider and resource contract

Accepted model IDs are `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`,
`gpt-6-astra`, `gpt-5.5`, `gpt-reserve`, and `codex-auto-review`. Credentials
come only from the explicitly supplied `OPENAI_API_KEY` environment variable.
LLaMEA uses its native `OpenAI_LLM` parser/query against
`http://127.0.0.1:8789/v1`, a 180-second SDK timeout and zero SDK retries.
Its five native API retries remain. Literal credentials are removed from the
native provider archive state; native deepcopy reconstructs the SDK from the
environment. EoH-S uses native `HttpsApi` through the local TLS relay at
`127.0.0.1:8790`, with a provenance-hashed public CA bundle. Its provider key
is an environment-backed property, preventing the native profiler's
`__dict__` dump from writing the key into logs.

Each template reserves 4 CPUs, 8 GiB memory, one evaluation slot and 512 PIDs,
with a 2,400-second outer deadline. Numeric libraries use one thread. LLaMEA
uses `max_workers=1`; native SMAC defaults to one worker. EoH-S uses one
sampler and evaluator. Native retries and parsing failures can exceed nominal
sample counts. In particular, joblib's single-worker execution does not supply
a reliable per-candidate hard timeout; the admitted outer cgroup deadline is
authoritative. Native generated programs execute under the existing trusted
worker policy; these profiles do not add a hostile-code sandbox.

Gateway `codex-native` compatibility records but does not enforce temperature,
top-p or output-token controls. Those values are not compute caps. Every
result remains **native evaluation, `canonical_evaluation=false`**. Native
scores across these distinct tasks/protocols are not a controlled comparison.

## Preparation and evidence

`scripts/deployment/prepare_llamea_eohs_pilots.py` writes 21 private templates
and pure source/input plans into a new directory. It never calls a model or
evaluator, changes a live control configuration, or submits a run. The private
operator installs separate Python 3.11 environments at
`/srv/arena/envs/{llamea-hpo,eoh-s}` while sources remain root-owned and clean.
IOH 0.3.22 requires NumPy 2; the LLaMEA environment uses NumPy 2.2.6, SMAC 2.3.1,
and the CPU XGBoost distribution. Its SMAC dependency `pyrfr` requires SWIG at
build time. EoH-S uses NumPy 1.26.4 and CPU-only PyTorch; its population module
also needs scikit-learn, omitted from the upstream setup declaration. No source
checkout is modified by dependency installation.

Prepared VM files:

- `/srv/arena/configs/llamea-eohs-pilots-20260921/templates.json` and per-profile
  `templates.json` files; the preparation manifest records source/plan hashes.
- `/srv/arena/build/llamea-eohs-envs-20260921/`: dependency freezes, install logs,
  clean-source checks and constructor-only conformance receipts.
- `/srv/arena/build/llamea-eohs-app-20260921/`: isolated preparation app snapshot;
  deployment and queue admission remain separate operator actions.

Validation covers actual native imports and constructors for all 21
configurations, inert LLaMEA transport calls for all seven IDs, and exact
dataset/source hashes. It does **not** execute native optimizer loops,
candidate evaluators, or model research. These checks establish configuration
compatibility, not a successful research run or measured scientific result.
