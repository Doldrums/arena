# Visible numeric results — 2026-09-21

The landing Results page previously emphasized integration counters and kept
canonical measurements inside chart tooltips. Native integration outcomes and
the separate local SCiEL research observer were absent from the published view.

The page now shows two numeric tables before the existing plots:

- SCiEL research: 165 measured observations, split across six evaluator protocols
  for circle packing, Heilbronn and oracle. Best-per-model and every-run views
  preserve each run's initial value, result, elapsed time and process state.
- Integration task results: 131 outcomes, comprising 21 canonical observations
  and 110 native projections, with task/system filters and pagination. Paired
  multi-objective outcomes retain their dimensions.

The integration snapshot covers 196 runs: 172 completed, 23 failed, one cancelled,
and none active. The 165 research observations are a separate population, not
added to the integration completion counters. Paused and stopped research runs
retain their observed outcomes. Elapsed research time includes pauses and is
not presented as compute time or monetary cost. Native task names do not imply
equivalent evaluator contracts or establish a cross-framework ranking.

Four additional native readers validate immutable evidence for AFlow, PromptAgent,
GEPA and MIPROv2 prompt pilots. Their held-out measurements preserve the native
selection and scoring protocols; they are not promoted to canonical evaluation.

Landing Results always uses the published projection, even with a saved key.
The experiment board link opens the separate owner-scoped workspace. Page loads,
filters and refreshes issue only a read-only overview request and launch no work.
The research section also works when there are no integration runs.

## Validation and rollout

- 169 Python tests and 48 subtests passed across results readers, publication,
  research projection and the board server.
- All 352 web tests and nine Worker API tests passed; TypeScript and the Worker
  deployment dry run passed.
- Chromium verified desktop (1440px) and mobile (375px) on both local surfaces
  and the VM tunnel, with and without a saved dummy key. Numeric values, native
  held-out accuracy, all-run pagination and filters were visible; no script errors
  or page overflow occurred. No private API request was made by the landing page.
- Eight runtime files were deployed after matching every preimage against
  commit `67648ae654d334f30864bbf7905db0a01172a155`, with automatic rollback on failure.
  The board restarted; the experiment worker stayed at PID 25447. The overview
  returned 200, private results without a key returned 401, and owner access
  returned 200 with all four new native metric projections present.
- VM deployment proof: `/srv/arena/build/results-values-20260921/proof.json`.

No experiments were launched, no private inputs or credentials were committed,
and no Cloudflare production deployment or PR merge was performed.
