# ADAS native MGSM gateway pilot v1

`adas-gateway-mgsm-v1` is a separate integration recipe for the original ADAS
implementation at `2702bee8fefda42255efc5be9f60e3bd3db96ae4`. The existing `adas`
recipe remains unchanged. This is a small CPU/API integration pilot, not a
reproduction of the paper or evidence of improvement.

## Native method and explicit seams

The driver calls pinned `_mgsm/search.py:search`: all seven original initial
strategies, a single meta-search generation, both native reflection calls and
the native debug branch (`debug_max=1`). Generated agents still execute through
the native `evaluate_forward_fn`, `LLMAgentBase`, prompt construction, JSON
parser and `score_mgsm`. Native bootstrap confidence intervals retain their
100,000-sample default. The native source checkout is never edited.

The original CLI restricts the meta model to three historical OpenAI IDs; inner
agents separately default to GPT-3.5. This explicit driver invokes the native
functions and binds the supplied agent API and meta requests to the same exact
selected gateway ID. The utility signature embedded in the meta prompt reflects
that model. An explicit different `LLMAgentBase(model=...)` is rejected, not
substituted. The seven IDs are `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`,
`gpt-6-astra`, `gpt-5.5`, `gpt-reserve` and `codex-auto-review`.

The local endpoint is fixed to `http://127.0.0.1:8789/v1`, with the scoped gateway
credential supplied through `OPENAI_API_KEY`. No credential is stored in plans,
seam metadata or the integration event trace. The native `json_object` request
is forwarded to the gateway, which translates it to Responses text formatting;
the native JSON parser remains authoritative. Responses must identify the exact
selected model and contain exactly one choice with text content; otherwise the
pilot stops without completed fitness. Actual model support must be
verified at admission: an offline fixture does not prove upstream availability.
The separately configured `codex-native` policy does not enforce the requested
temperature, token limit or stop control. These are recorded as unenforced, not
presented as sampling or compute guarantees.

Transport uses OpenAI SDK timeout 330 seconds and `max_retries=0`. A dispatched
transport failure has unknown outcome/cost and aborts the pilot. It does not
become a zero score or trigger native unbounded rate-limit backoff. Native JSON
and generated-code errors retain native evaluation/debug behavior.

## Official data and split

Data comes from Google's [official MGSM repository](https://github.com/google-research/url-nlp/tree/452a21ad3dae5668c06ceeac21ff073e1e40f9be/mgsm),
commit `452a21ad3dae5668c06ceeac21ff073e1e40f9be`. MGSM contains translations of
the same 250 GSM8K problems; the source release uses
[CC-BY-4.0](https://github.com/google-research/url-nlp/blob/452a21ad3dae5668c06ceeac21ff073e1e40f9be/mgsm/LICENSE).
Attribution: Shi et al., *Language Models are Multilingual Chain-of-Thought
Reasoners* (2022), derived from GSM8K by Cobbe et al. (2021).

`registry/datasets/mgsm-adas-pilot-v1.json` contains four unmodified source
question/answer pairs, attribution, exact source URLs/file hashes and row hashes.
Its SHA256 is `67899701f97b7890ebd99bdb5b1098be4e86e3a846ed076ed9c675ce18588a96`.
The official English and Spanish TSV files also match ADAS's pinned copies
byte for byte. The fixed split was selected before any model run:

| Phase | Zero-based source row identities |
|---|---|
| Optimization | English row 0; Spanish row 1 |
| Heldout | English row 2; Spanish row 3 |

Underlying rows are disjoint across languages. A global shuffle of translations
would not provide this property. The driver inverts the known native shuffle to
feed these explicit slices; the native shuffle and evaluator slicing still run.
Only optimization examples are returned by the data-provider seam while search
is active. After search, selection uses the highest completed native optimization
mean, with stable native archive order for ties; `selection.json` is written
before the single selected code hash is evaluated on heldout.

At this ADAS pin, exhausting a debug loop can leave a newly proposed code string
next to the preceding code's accuracy. The integration therefore selects only
archived hashes with matching completed evaluation records. It never rewrites
the native archive or parses its rounded bootstrap-CI strings into scores.
The native all-archive test loop is intentionally not used for selection.

The scorer is unchanged: comma removal, trailing decimal-zero stripping when
a decimal point is present, then exact string equality. No answer extraction,
whitespace normalization or substring matching is added. The result is native
MGSM accuracy, not an Arena canonical receipt. Four public examples cannot
establish statistical generalization or rule out pretraining contamination.

## Bounds and admission boundary

| Scope | Bound |
|---|---|
| Initial strategies | All seven native strategies |
| Meta generations / debug maximum | 1 / 1 |
| Native evaluator workers | 1 |
| Questions per evaluator invocation | 2 |
| Dispatched supplied-API requests | 128 |
| Evaluator invocations | 32 |
| SDK timeout / automatic retries | 330 seconds / 0 |
| Whole-process template deadline | 3,600 seconds |
| Worker resource request | 4 CPUs, 8 GiB, 512 PIDs, one evaluation slot |

Request/evaluator counters are cooperative instrumentation. Native generated
Python executes in the worker process, with access to the scoped gateway key;
it can bypass in-process hooks or inspect the public dataset/source checkout.
There is no claim of adversarial sandboxing, confidential heldout storage,
hard per-model API authorization, or token/dollar caps. The outer runtime supplies
the process-group deadline, and reviewed worker/cgroup containment is required.
Do not treat a `ready` template as permission to admit a run. No templates were
admitted during this preparation.

## Reproducible preparation and offline conformance

Use a separate Python 3.11 environment. The observed fixture installed
`openai==1.90.0`, `numpy==2.2.6`, `backoff==2.2.1`, `tqdm==4.67.1`,
`httpx==0.28.1`; save its complete dependency freeze with the proof. No native
model call or generated research program is required to prepare templates.

```sh
python scripts/deployment/prepare_adas_mgsm_pilot.py \
  --root /srv/arena --destination /absolute/new/preparation

python scripts/deployment/check_adas_mgsm_pilot.py \
  --source /absolute/pinned/adas --output /absolute/new/offline-proof

python -m pytest -q tests/frameworks/test_adas_mgsm_gateway.py
```

Preparation expects `/srv/arena/sources/adas` at the exact clean pin and
`/srv/arena/envs/adas-gateway/bin/python`. It emits seven plans/templates and a
hashed dataset copy, never changes live control configuration and never queues
work. Plans capture their actual environment and integration code: regenerate
against the final approved installation before admitting them.

The SDK fixture blocks network/subprocess operations and uses real OpenAI
`httpx.MockTransport`. One complete native cycle performs 55 mock requests,
eight optimization evaluator invocations and one heldout invocation (18 question
scores); both native model roles are additionally exercised for the remaining
six IDs. A separate real-SDK 503 fixture proves one request, no retry, no completed
fitness and no heldout. Fixture scores are deliberately controlled and are not
research results.

Runtime artifacts include native `mgsm_run_archive.json`, integration
`provider-seam.json`, bounded-count request/evaluation events, `selection.json`,
`heldout.json` and `pilot-status.json`. Native archives preserve generated code;
the integration request trace records only roles, exact model, token usage when
reported, durations and safe exception classes. Unknown provider outcomes are
not assigned estimated cost or successful generations.

## Recorded preparation, 2026-09-21

The VM fixture completed as UID 998 with Python 3.11.16 in
`/srv/arena/envs/adas-gateway`. It used the clean source tree
`2a6965d31bd8fb97c0cded7dc02f8c0776239dad`, 67 successful mock HTTP requests plus
one deliberately failed mock request, zero real provider calls and zero network
attempts. One subprocess attempt was blocked by the fixture audit hook; no
subprocess was executed inside the protected mock phase. The actual native
executor failure test verified that its already queued second question cannot
dispatch after a fatal first request.

The refreshed proof includes strict response model/cardinality/content checks;
17 focused VM tests and 41 combined local driver/recipe tests passed.
Proof: `/srv/arena/build/adas-mgsm-conformance-20260921/native-proof-response-check/proof.json`,
SHA256 `91584dfba26d71708431fe3d51168965cb812fc4268317b4694af7a5ff0232b6`.
Dependency freeze: adjacent `../environment.freeze.txt`, SHA256
`3cb749b701c5ee03c5bf92dc4d4f4ea7e1e35dc68ace0bb486015e5c85ed5f89`.

Seven refreshed pure templates are in `/srv/arena/configs/adas-mgsm-response-checked-20260921`;
`preparation.json` SHA256
`347c26cd38d021c6aaf3555fadd8119bd7de37a66c2cbe10581cf5e8abe599d4`.
Their plans point to the isolated review package at
`/srv/arena/build/adas-mgsm-review-20260921`, not the active application. They
must be regenerated against approved installed code before admission. The
environment is fingerprinted but not an immutable image (`environment_locked`
remains false). No live app/control configuration or queued run was changed.
