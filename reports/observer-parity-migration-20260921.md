# Native observer parity update — 21 September 2026

The deployed Arena observer lagged behind the current native SCiEL board. This
update brings the newer data semantics into the existing Arena Experiments
interface. It does not change CSS, HTML, sidebar navigation or the Tasks design.

## Source boundary

- Prepared Arena observer chain: `1e1c95d0771d7c1aa2a5fe42a905f4b54f412111`.
- Native SCiEL v16: `63055fb9e40d8d70c5dbf5228afd2caf6d749d34`.
- Arena deployment before this update: `f7a866843736bca7be5cc2ab313bc7a6e89acc59`.

Only observer functionality and its tests were extracted. Historical Tasks UI
commits were excluded. The existing Cloudflare unavailable/retry states and
effort updates from heartbeats remain intact. The observer still has no SCiEL
Engine or model-provider dependency and cannot execute candidate programs.

## Changes

- Distinguish subscription calls without a supplied USD price from missing cost
  records; retain known monetary subtotals and display recorded token usage.
- Recognize newer and historical task identities for packing evidence.
- Support independent research sharing, continuation queues, transfer stages,
  pending model review and receipt-bound comparison warnings.
- Verify compact paired measurements and whole observation rows through pure
  compatibility helpers, preserving evidence hashes and schema names.
- Resolve physical metrics for candidates produced by research tools through
  their canonical evaluator records.
- Label non-improving near-output refusals correctly and expose task resolution.
- Recognize recorded research contracts through `espalier-3.59`.
- Display precise reference gaps, distinguish comparison groups and link to the
  best saved program using the existing Arena table and disclosure styles.

## Validation

- Python observer suite: **649 passed, 2 skipped, 138 subtests**. Includes import
  independence, canonical-metric tampering and new evidence-schema checks.
- Targeted frontend suites: **89 passed**; after preserving the existing table
  styling, the affected benchmark/effort suites passed again (**13 tests**).
- Independent review confirmed frontend/backend field agreement and relative,
  hash-bound artifact resolution after moving archives to another machine.
- `git diff --check` passed. No experiments were launched by implementation,
  validation or registry changes.

## Archive relocation

Native `run_id` and artifact hashes survive relocation. The observer's opaque
public run identifier is derived from the journal's absolute path, so links to
Mac-local board IDs must be replaced by IDs returned by the server's run list.
Preserve the complete `artifacts`, `research_tools` and `.parallel` trees and
their original bytes; missing or mismatched evidence must remain unavailable.

A cold discovery of 203 local archives took approximately 27 seconds on the Mac,
with about 424 MB peak RSS; warm discovery took 3.9 seconds. Warm the VM observer
directly before sending Cloudflare traffic, whose upstream header deadline is
10 seconds. Imported files are observation snapshots, not remote execution or
proof that a Mac process is running on the VM.

## Deployment verification

Code commit: `3225c8b8f2dbd14f6548f09aa8d5be731c1caf77`. The observer runs
from `/opt/arena/observer-releases/3225c8b8`; the experiment worker keeps its
previous release and PID. The verified import contains **203 runs and 129,585
files**. Every extracted file matched its captured size and SHA-256 before the
snapshot directory was published read-only to the board.

The server now exposes **217 runs**: 203 imported records plus its existing 14.
Cold warmup took 45.18 seconds on the VM; a subsequent full run-list request took
2.34 seconds. The board used approximately 359 MB at the postdeployment check.
Board, worker and private tunnel services are active; worker PID `25447` did not
change. The local Arena observer was also reloaded, preserving its four
additional local records for a total of 207.

Cloudflare deployments:

- Main Worker: `cad03042-4e2d-466f-969f-bc267780f2c7`.
- Existing expiring debug Worker: `a66b602f-a9e8-44f6-8c9e-1d6b5dd04344`.

Authenticated Chromium verification rendered all 217 rows, opened a v16 circle
packing run, displayed its recorded metric `2.623714` and `Subscription` cost
status, fetched saved program source with private/no-store headers, and observed
two SSE snapshots across reconnection without browser errors. Unauthenticated
and logged-out observer requests returned 401; writes returned 405 and control
routes remained unavailable. The main hostname retained its university Access
sign-in gate. No CSS or HTML files changed in this migration.
