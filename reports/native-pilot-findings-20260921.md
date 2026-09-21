# Native pilot findings — 2026-09-21

These are deployment and integration observations from the private worker, not
paper reproductions or a cross-framework leaderboard. Successful transport,
native search completion, valid candidates and canonical evaluation are distinct
claims. Historical failed runs remain intact when a new attempt is submitted.

## Gateway contention

The first expanded batch allowed 12 simultaneous research processes while the
local model gateway admitted at most eight upstream requests. A research process
can issue more than one request concurrently. The worker's active-run ceiling
was reduced to four; already running processes were allowed to finish. This
reduces contention but does not establish an account-wide throughput limit.

Four host SCiEL runs stopped with persisted provider receipts containing HTTP
429 at the next research-generation request. Their 45 completed canonical
evaluation receipts remain valid artifacts (13/12/12/8, respectively):

| Model | Run |
| --- | --- |
| gpt-5.6-terra | `48c933d204d24bafa7040cd78fcd8e07` |
| gpt-5.5 | `58c88f2ffa7e495da65a2ba832f657e9` |
| gpt-reserve | `3e73b47c9dc445f595fae519789f1754` |
| codex-auto-review | `f2b2aee83510484a866aa12a113e7f6b` |

SCiEL conservatively retained an unknown generation outcome. These records were
not reset or resumed as though no request had happened. The smaller, separately
approved private-image matrix uses new run IDs and a four-call native budget.

Five EoH runs exhausted native retry backoff during the same interval. The
original FunSearch pilot (`784cb939054546d08ee0b66865c7e609`) explicitly recorded
`gateway_busy`. The kitft reimplementation (`562b25c3003c4e5aaa137d45bb962a06`)
suppressed the initial provider failure and subsequently failed when dereferencing
an absent response. Two FunSearch and five EoH retries were submitted as separate
queue records after the load dropped. The private admission receipt is
`/srv/arena/build/gateway-contention-retries-20260921.json`.

Contemporaneous logs establish local saturation; the old gateway audit format
does not distinguish the source of every individual 429. It would be incorrect
to attribute every rejected request to an upstream account quota. The updated
gateway audit records sanitized fixed error codes, including local versus
upstream limits, without recording credentials, prompts or generated text.

## SCiEL private-image Luna: dispatched generation failed

Run `560c5df96d754b9aadec56df6bedf5b1` stopped on its second G request.
The native dispatch began at 06:40:19.132 UTC and returned HTTP 500 at
06:42:14.552 UTC after 115.419 seconds; the recorded local queue wait was
0.000891 seconds. The contemporaneous gateway audit records request
`0cf10b7885cf459389711d844bfac118`, model `gpt-5.6-luna`, status 500 and
unknown usage. This was neither a canonical evaluation failure nor the local
300-second timeout. The old running gateway did not record the exception class
or error code, so its underlying internal exception cannot be recovered from
these records.

SCiEL retained `generation_dispatch=unknown` and
`current_call_cost_unknown=true`, persisted its wave stop and exited. No
successful generation or zero-cost claim follows from that failed response.
The authoritative broker receipt is
`/srv/arena/releases/engine-receipts/560c5df96d754b9aadec56df6bedf5b1.json`,
SHA-256 `ac325a9d8d326f736aaa2836e57067565e85b03f728c6e045becad4bab4a6270`.
All 54 published artifact hashes matched, and cleanup was confirmed. Two
canonical SAT receipts remain valid at score 1.0: the initial seed and one
returned generated candidate. The seed already scored 1.0; there is no measured
improvement. The failed dispatched generation was not automatically retried.

Future gateway diagnostics should retain bounded exception-class and request
timing/correlation metadata without prompts, provider bodies or credentials.
This diagnosis did not change the provider service or historical artifacts.

## Original FunSearch: client timeout shorter than gateway deadline

Retry run `9d3f5d9cd4d14f3e95b9826c7a22bf04` ran from 06:30:25.058 to
06:33:27.805 UTC, 182.747 seconds. The installed SDK raised `ReadTimeout` while
waiting for response headers, followed by `APITimeoutError`. The original
pilot's client used a 180-second timeout and no SDK retries, while the gateway
allowed 300 seconds and buffered this nonstreaming completion.

Native evidence records one attempted sample, zero returned samples and one
sandbox call for the seed. The native admissible-set seed score 125 was
registered in two islands; these are not two evaluations. There are no
canonical receipts or generated candidate results from this run. Its retained
`results/native-result.json` SHA-256 is
`34beaf333fbc272039af5a9a2fd4de80f5e3ceb25e491efc20f30030e8bf9f8b`;
`results/native-trace.jsonl` is
`1da6d46c79622266524d025438322864162fc71eb53355207f682356164ebad8`.

At 06:33:34.313 UTC the gateway recorded a Sol response with status 499 and
195 input / 5,657 output tokens, request
`6fce10f1e48142cfafcb9fa68014eedc`. Its timing and input size fit this timeout,
but the old audit lacks start time and request correlation for the failed
client, so that association remains an inference. It is not a returned native
generation, proof of zero spend, or an exact billable-cost measurement.

The separately versioned `funsearch-original-timeout-v2` recipe raises the
client timeout to 330 seconds, above the expected 300-second gateway deadline,
with `max_retries=0`. It retains six generated samples, the same native task,
search/scoring pipeline and a 2,400-second outer runtime template. Existing
original/reimplementation recipe hashes and their default 180-second behavior
are unchanged. Seven new templates are prepared only; this work did not admit
runs, call a provider or alter live configuration. See the
[versioned transport notes](../docs/frameworks/funsearch-timeout-v2.md).

## MCTS-AHD prompt/evaluator mismatch

Cancelled run: `4c35e2423b68411395d5b49fd1aa98d5`.

At the pinned native source, `prompts/bpp_online/func_signature.txt` requested
`priority`, while `problems/bpp_online/eval.py:9` imported `priority_v2`.
Generated candidates followed the requested name. Of 35 inspected distinct
evaluation logs, 32 reported the import failure and three reported
indentation errors. At cancellation, all 92 recorded evaluation attempts had
non-finite failure fitness and initialization had not completed.

The native initialization retry loop in `source/evolution_interface.py` did not
check the configured `max_fe=4` target. The run was explicitly cancelled and
terminated with return code −9. Remaining models were not admitted on that
profile. A new version must align the requested function signature with the
unchanged evaluator and enforce a separately recorded proposal-attempt bound.
The historical run and its inputs must remain unchanged.

HTTP 200/429 log-line counts are not counts of billable model calls or distinct
successful research generations and are not used as such here.

## CoEvo history accounting

Run: `cecf087e405246028b04e6e5d9a7cde3`.

At initialization the native history contained eight entries representing four
distinct retained solutions, each registered twice: once by CoEvo's
`_register_chain`, then again by the installed evotoolkit population registration.
Four valid history rows therefore represented two distinct retained valid
solutions, not four independently verified evaluations. Failed intermediate
attempts are not fully represented by this retained population.

The initial generation and first evolutionary step also target the same
`history/gen_0.json` filename. Before the later checkpoint, the operator saved
the unmodified 41,532-byte initialization file outside the native run tree:

`/srv/arena/build/coevo-history-audit-20260921/4b8175ae80dd0c8cf76f847a60dd86b1255dbec41fac62742d687a6dcb66b8a0.json`

The filename is its SHA-256. Native outputs were not edited. Subsequent adapter
work must preserve checkpoint history and distinguish raw rows from distinct
retained candidates; neither count establishes all physical evaluator calls.
The native catch-all retry handler does not retain enough evidence to attribute
its early failures to transport versus parsing.

## Completed integration evidence

- Private SCiEL image run `5a72d1e3d80749fbbffb10f6174572b6` completed; all
  139 published artifact hashes matched the privileged broker journal. Seven
  canonical SAT evaluations were valid. The initial solution already scored
  1.0, so this is not evidence of improvement. See the dedicated
  [image conformance report](private-image-conformance-20260921.md).
- All seven Shinka model pilots completed. The separate
  [reader report](shinka-reader-pilot-20260921.md) distinguishes native database
  rows, generated candidates and canonical receipts.
- CodeEvolve run `d6f682b8fe674e9684dea341016621cb` completed four native epochs;
  the seed and four generated programs were evaluated without execution errors.
  Its native circle-packing metrics are not canonical Arena receipts.

Queue totals change as batches progress. The live queue, per-run immutable
snapshots, native artifacts and root-owned broker receipts are the authoritative
records; this report does not replace them.
