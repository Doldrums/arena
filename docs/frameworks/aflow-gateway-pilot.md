# AFlow GSM8K native graph pilot

The separate `aflow-gateway-gsm8k-v1` recipe retains the official AFlow source at
`3f457218fc716093fe53f6df8a5d5e6379d66346`. The existing `aflow` recipe is unchanged.
The profile invokes the pinned `Optimizer.optimize("Graph")`: native graph
selection, experience feedback, graph generation, operators and evaluation remain.
This is a preparation and conformance profile, not a completed research run.

## Data and metric

The input is the existing hash-pinned `gsm8k-prompt-pilot-v1.json` bundle (SHA256
`98abad8a6fc5b24172c329f257815fe0c4c3b6756716a9de980d4ed1be96a974`). Its source is
[OpenAI GSM8K](https://github.com/openai/grade-school-math/tree/3101c7d5072418e28b9008a6636bde82a006892c),
MIT license. It retains original rows, indices and hashes. Eight validation
examples come from the official train split; eight question-disjoint heldout
examples come from the official test split. The separate eight train examples in
the shared bundle are unused by AFlow. There is no assertion that a model has not
seen public GSM8K during pretraining.

**AFlow's native metric is used, not the official GSM8K `####` string metric**:
`benchmarks/gsm8k.py` extracts the last number, converts to float, and compares with
absolute tolerance `1e-6`. This differs from the GEPA/MIPRO pilot metric. Their
scores are not a controlled cross-framework comparison.

The driver creates only `gsm8k_validate.jsonl` before optimization. After both
rounds have native result and experience records, native `DataUtils.get_top_rounds`
selects the highest mean validation score, with its existing stable tie behavior.
`selection.json` freezes the round, score and graph/prompt hashes before the test
file is materialized. The seed and selected graph are then evaluated through the
unchanged native `Evaluator.graph_evaluate(is_test=True)`, once each, or once total
when they are the same graph. Heldout does not select a graph or affect search.

The upstream `Optimizer.test()` hardcodes round1 and a separate `workflows_test`
directory. This profile explicitly calls the native evaluator after selection;
it does not claim to run that hardcoded test helper or replicate the paper.

## Provider and limits

All optimization and execution roles use the same exact selected ID from:
`gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-6-astra`, `gpt-5.5`,
`gpt-reserve`, `codex-auto-review`. Credentials remain an `OPENAI_API_KEY`
environment reference to the scoped local gateway at `http://127.0.0.1:8789/v1`.
The provider seam wraps the native `scripts.async_llm.AsyncOpenAI` constructor;
native AsyncLLM, XML/text/code formatters and operator prompts are not replaced.
Each SDK call uses a fresh async client because native optimization creates a
new event loop per round. SDK retries are zero, per-request timeout330 seconds (above the gateway’s300-second deadline),
and concurrent SDK requests are serialized in each native round.

Two native optimization rounds produce a fresh seed assessment plus at most two
new graph assessments, each over eight validation examples. There is one native
validation repetition; graph-parent sample count4 and the native probability
formula are unchanged. Native benchmark concurrency is explicitly1. An independent
cap admits at most40 problem evaluations and192 SDK requests, including failed
attempts and all roles/heldout. Native parser/evaluator retries remain inside that
shared request cap. The control template sets2400 seconds,4 CPUs,8192MiB,512 PIDs
and one evaluation slot. Sampling controls `temperature` and `top_p` are recorded
but not enforced by the gateway; they are not provider compute limits.

Budget exhaustion escapes native retry loops and exits75 with a partial receipt.
A return from the native optimizer without all three round results and both new
experience records exits76 (`native_incomplete`); it does not evaluate heldout or
claim native completion. Native completion and heldout completion are separate.
The outer control deadline remains the bound for stalled native/generated code.

Upstream unknown model prices default to zero. Native CSV cost columns are
retained as native estimates, while `cost_usd` remains null. SDK usage/admissions
are recorded separately and are not billing records.

## Native limitations retained

At this pin, GraphOptimize's XML fields default to empty strings, so malformed
responses with missing tags can parse as an empty dictionary and fail later in
the native round. Also, CodeFormatter returns `response`, while Programmer later
looks for `code`; its "No code generated" path can therefore occur. The fixtures
expose these native semantics; the adapter does not repair operators or replace
graph search. Custom and ScEnsemble remain available native operators.

The three tracked native history files are empty placeholders at this pin. The
driver verifies that only round1 exists and all three files are exactly empty,
then removes those placeholders only in the isolated run workspace and records
their hashes. Nonempty prior results are rejected. Generated graph code uses the
native relative `workspace.GSM8K` package, preserving upstream import behavior.
Native code execution requires the trusted worker boundary; the Programmer
string-based import filter is not a security sandbox.

## Preparation and conformance

Use a clean pinned source and an isolated Python3.11 environment with the upstream
`requirements.txt`. Keep `pip freeze` and `pip check` evidence. Planning imports no
AFlow code and makes no model requests:

```sh
python scripts/deployment/prepare_aflow_gateway_pilots.py \
  --destination /srv/arena/configs/aflow-gateway-pilots-20260921
```

`check_aflow_gateway_pilots.py` uses the actual installed OpenAI SDK with mock HTTP
responses and an audit-hook network denial. It verifies all seven model aliases,
both native roles, seed evaluator, text/XML/code parsing, cross-event-loop calls,
and a pre-exhausted budget escaping actual native retry layers. It also runs a
complete native seed-plus-two-round cycle using reviewed inert graph code and
fixed mock responses, including native graph writes/imports, validation selection
and heldout. No model-generated code or live model response is used. These
fixture values are not scientific results. The native source is copied before imports so fixture
logs and data never dirty its pinned checkout.

## Recorded preparation, 2026-09-21

The isolated VM environment `/srv/arena/envs/aflow-gateway` passed `pip check`.
The pinned source remains clean. The final network-denied fixture ran as worker
UID998 and exercised six mock SDK requests for each of seven models. It also
completed the real native optimization/evaluation path for `gpt-5.6-sol` with
known inert graph code: rounds1/2/3, validation-selected round2 frozen before
heldout, then seed and selected graph heldout evaluations. The full cycle used
42 mock SDK requests,24 validation and16 heldout problem evaluations. The
completed receipt records native and heldout completion. Predetermined fixture
scores are not model performance or research results; live model calls are zero.

Final proof:
`/srv/arena/build/aflow-gateway-conformance-owner/full-cycle-sdk330-final-20260921/conformance.json`,
SHA256 `bc4365b1cb3f41cddc97eb5498e6f963f604f537e5fcf0a1052110678344d0fc`.
The adjacent `full-cycle-proof.json` contains event order, inert graph hash,
selection hash and completed-receipt hash. Driver SHA256:
`4e78e48ead9cf873a3df4e7d85b5d93dfbae7e523ff2ac5ac0940f992d1ce678`.

Seven final templates with SDK timeout330 are prepared at
`/srv/arena/configs/aflow-gateway-pilots-sdk330-20260921/templates.json`, SHA256
`c3f0f0a744725cafd92b71ca6ff84a4aa521164b2884a211fbd943dd4ff072b4`.
Worker-UID repeat planning reproduced every plan hash and passed control-template
schema validation without writing live control state. The adjacent
`operator-validation.json` SHA256 is
`649bc4d731a8ff0edf131a5efdf5e03882f516babe0e4479f5a6442aaaeb311a`.
Plans bind to `/srv/arena/build/aflow-gateway-app-20260921`, so promotion to the
active application requires new plan verification against that application's
paths and integration hashes. Earlier180-second preparation/proofs remain in
their original directories as superseded pre-admission evidence. No template was
admitted and no service changed.
