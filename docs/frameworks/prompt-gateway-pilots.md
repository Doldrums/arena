# GEPA and DSPy MIPROv2: small native prompt pilots

Two new recipes preserve the existing registrations and historical recipe
hashes:

| Recipe | Native source pin | Search configuration |
|---|---|---|
| `gepa-gateway-gsm8k` | `gepa-ai/gepa` at `15ee314f9c7d34ec153b809d401f42f55c4dcd76` | Native `gepa.optimize`, Pareto candidate selection and reflective mutation; metric target 24, reflection minibatch 3, seed 9 |
| `miprov2-gateway-gsm8k` | `stanfordnlp/dspy` at `40a6e168914a7b81a78b1a081d93f26de18c8d0d` | Native `MIPROv2.compile`, 3 candidates, 3 Optuna trials, at most 1 bootstrapped and 1 labeled demonstration, explicit full-validation evaluation, seed 9 |

These use native optimizer APIs and task adapters. They do not reproduce the
original GEPA or MIPRO paper protocols. MIPROv2 is named explicitly; it is not
presented as the original MIPRO 2024 implementation. Three demo candidate sets
are intentional: the pinned DSPy helper creates the zero-shot and labeled sets
first; its genuine bootstrap branch begins with the third set.

The task data is a genuine subset of [OpenAI's GSM8K repository](https://github.com/openai/grade-school-math/tree/3101c7d5072418e28b9008a6636bde82a006892c),
at commit `3101c7d5072418e28b9008a6636bde82a006892c`, under its MIT license.
The immutable bundle
[`gsm8k-prompt-pilot-v1.json`](../../registry/datasets/gsm8k-prompt-pilot-v1.json)
includes the license, untouched questions/answers, source file hashes, source
row indices and row hashes. Its SHA-256 is
`98abad8a6fc5b24172c329f257815fe0c4c3b6756716a9de980d4ed1be96a974`.

Selection uses only the question: for each official source split, sort by
SHA-256 of `version + NUL + source_split + NUL + exact_question`, breaking ties
by original row index. The first 8 official-train rows become training, the
next 8 validation, and the first 8 independently ranked official-test rows
heldout. All 24 questions are distinct. Answers and observed model scores were
not used to choose them.

Both pilots supply the original [GSM8K `extract_answer` / `is_correct` metric](https://github.com/openai/grade-school-math/blob/3101c7d5072418e28b9008a6636bde82a006892c/grade_school_math/dataset.py).
It takes the **first** `#### ` numeric match, removes commas, and compares
strings. It does not select the last number or coerce decimal strings to
integers; a missing marker is invalid. GEPA scores its textual completion;
DSPy scores the program's `answer` field. This is an explicitly supplied common
task metric, not a claim that the frameworks' bundled GSM8K example metrics
are identical.

Only train and validation records reach optimization, demonstration
bootstrapping, reflection or candidate selection. After the native optimizer
returns, the frozen seed and validation-selected programs are each evaluated
once on heldout. Heldout does not feed back into the optimizer. Raw heldout
predictions are written incrementally; an interrupted pass has `accuracy:null`
and separate expected/completed counts. Optimizer completion and heldout
completion are recorded separately.

Eight examples per split establish a small integration protocol, not a reliable
benchmark estimate. Public GSM8K may be present in pretraining. Identical
splits and model names alone do not establish controlled scientific comparability
between different native search budgets and prompt representations.

The provider seam preserves the exact seven gateway model identifiers. It
uses the local `http://127.0.0.1:8789/v1` endpoint and an `OPENAI_API_KEY`
environment reference. Native multi-completion calls are transported as ordered,
sequential `n=1` requests; all returned choices retain their order. A shared
transport budget survives native program/LM copies. SDK retries are zero,
request timeout is 180 seconds, and a hard admission limit of 128 gateway
requests ends the pilot with exit 75 on exhaustion. Requests, example metric
calls, native trials and billing are separate quantities.

Native GEPA stopping is checked between iterations, so a complete
proposal/validation may overshoot its metric target. MIPROv2 bootstrap,
instruction proposal and initial validation require calls outside its three
Optuna trials. Both have a 2400-second outer deadline and reserve 4 CPUs,
8 GiB, one evaluation slot and 512 PIDs. GEPA's callable adapter is serial;
DSPy uses one evaluation thread; the shared transport lock prevents parallel
provider bursts. Native optimizer logic is unchanged.

The gateway records but does not enforce temperature, token limits or top-p.
Returned token usage is retained per request when available; monetary cost is
unknown. GEPA's native `TrackingLM` callable wrapper has its own approximate
token counters and zero-cost placeholder: these are not billing evidence.
The new `gateway-usage.json` keeps that distinction explicit.

DSPy's transport plugin uses the supported `BaseLM.forward` interface at the
pinned DSPy 3.4 revision, which marks that interface deprecated for a future
release. Its state is saved without credentials; native copies share the
runtime transport. A future DSPy pin needs another compatibility review.

Preparation and conformance are explicit, separate commands:

```sh
python scripts/deployment/prepare_prompt_gateway_pilots.py \
  --root /srv/arena \
  --destination /srv/arena/configs/prompt-gateway-pilots-20260921

/srv/arena/envs/gepa-gateway/bin/python scripts/deployment/check_prompt_gateway_pilots.py \
  --framework gepa --source /srv/arena/sources/gepa \
  --dataset registry/datasets/gsm8k-prompt-pilot-v1.json \
  --output /srv/arena/build/gepa-conformance-new
```

Use the MIPRO environment, `--framework mipro` and its source for the second
fixture. Conformance denies network access and uses actual SDK mock transports,
native parsers, metrics and constructors. Both passed all seven exact model
IDs on the VM, including DSPy two-choice transport, program copying and
credential-free JSON persistence. No native optimization or model call was
performed. Environments were installed from separate build copies; the source
checkouts remain clean and root-owned.

VM templates are at
`/srv/arena/configs/prompt-gateway-pilots-20260921/templates.json`.
Environment install logs and dependency freezes are at
`/srv/arena/build/prompt-gateway-envs-20260921/`.
Final native fixture receipts are under
`/srv/arena/build/prompt-gateway-conformance-owner/{gepa,mipro}-final-20260921/`.
Preparation does not edit live control configuration or admit runs.
