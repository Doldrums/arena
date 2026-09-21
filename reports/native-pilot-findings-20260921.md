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

## MCTS-AHD prompt/evaluator mismatch

Cancelled run: `4c35e2423b68411395d5b49fd1aa98d5`.

At the pinned native source, `prompts/bpp_online/func_signature.txt` requested
`priority`, while `problems/bpp_online/eval.py:9` imported `priority_v2`.
Generated candidates followed the requested name. Of 35 inspected distinct
evaluation stderr files, 32 reported the import failure and three reported
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
