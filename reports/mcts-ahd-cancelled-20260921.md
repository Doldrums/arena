# Cancelled MCTS-AHD pilot: preserved failure evidence

Run `4c35e2423b68411395d5b49fd1aa98d5` used the original
`mcts-ahd / gateway-cpu-pilot` profile. The control record is `cancelled`,
with `cancel_requested=true` and return code `-9`. The run did not finish
native initialization and recorded no finite native objective.

The source mismatch is exact: pinned
`prompts/bpp_online/func_signature.txt:1` requested `priority`, while
`problems/bpp_online/eval.py:9` imports `priority_v2` from the candidate module.
`source/evolution_interface.py:151` retries initialization without checking
`max_fe`; the native tree loop checks that target only after initialization.
The source revision is `ee9c4f424503c65a5fd2b899e6620ce86079fedb`.

The final evidence snapshot, taken at 2026-09-21 06:01:03 UTC, contains:

| Observation | Count | Scope |
|---|---:|---|
| Native logged evaluation outcomes | 92 | All 92 reported `inf` |
| Unique evaluation stdout files | 35 | Filenames derive from `hash(code)`; repeated code reuses files |
| Stdout files with missing `priority_v2` import | 32 | Unique files, not unique evaluations |
| Stdout files with `IndentationError` | 3 | Unique files, not unique evaluations |
| Literal HTTP 200 log events | 185 | Transport log events only |
| Literal HTTP 429 log events | 297 | Transport log events only |

HTTP log counts do not establish unique model calls, paid requests, tokens or
cost. The file counts do not establish physical evaluation counts because
native filenames are reused. This report makes no billing estimate.

Seventy-three files were copied to a separate private archive without changing
the original run, its receipt, configuration, queue entry or logs:

`/srv/arena/configs/mcts-ahd-cancelled-evidence-20260921/`

The archive's `manifest.json` records each original relative path, byte size
and SHA-256. Every copy was checked against its source before and after copying.
Manifest SHA-256:
`9d5e080133ab2e88a300c51a33c5e18c0c58e725c443f65e6a33cc28c17f88a5`.

The original recipe's canonical JSON SHA-256 was independently compared
between the local catalog and deployed application after creating the v2
variant; both are
`74f866297f6529038cbf86c69a127c2bfc64d10184768fd0226332439d509e98`.
The v2 variant is a new recipe, not a rewrite of the cancelled experiment.
