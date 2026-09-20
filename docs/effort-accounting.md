# Discovery effort in the observer

`arena-run-effort/1` is a read-only projection of saved cooperative-I/O receipts.
It does not run, repair or resume an experiment. The selected experiment receives
the projection on snapshots and runtime frames; the run list uses cheaper, clearly
labelled committed accounting and configured models.

The two scopes are intentionally different:

- `total`: completed physical calls across all recorded waves, plus pending calls
  and charges whose amount is unknown, at the observer timestamp.
- `to_best`: the same all-branch history cut at the exact completion time of the
  unique source-, task-, score- and case-bound evaluation of the selected best.
  Calls dispatched before that cutoff but completed later remain pending in that
  historical view. The program's own generation charge is never used as its
  discovery cost.

`physical_llm_calls` counts terminal returned/error receipts, not logical research
steps or provider-internal retry attempts. `evaluator_cascades` includes canonical
seed, fresh starts, retries, failures and remeasurements. Smoke/full/confirmation
stages within a cascade are not counted as separate candidates. Ordinary logged
iterations and the best candidate's owning iteration are separate fields: in a
parallel wave an evaluator can return before iteration 1 is committed.

The total includes research planning, analysis and unrelated parallel branches.
LLM USD is recorded spend, with missing/pending charges and non-provider estimates
explicitly marked. Local model, evaluator CPU and infrastructure dollar costs are
unknown. Elapsed wall time includes pauses and is never presented as CPU time.
Model identities come from returned receipts where present, otherwise the saved
physical request; pending calls therefore carry the requested model identity.

Committed receipts must match their journal owner before that wave's completion,
in the same run and segment, within a hash-bound committed journal prefix. Active
receipts also require the current wave's baseline/checkpoint binding. A missing,
modified or orphan receipt makes history partial; legacy runs without receipts
remain unknown. This is a non-atomic observational snapshot, not a billing audit.

Published comparisons carry independent `arena-reference-effort/1` metadata.
Reported training/generation budgets retain their units and scope; generated
samples are not relabelled evaluated programs. Unknown baseline cost, calls and
first-attainment effort stay unknown. Only native measurements at the same saved
tolerance share an ordered comparison group. Strict/other-tolerance references
remain separate and receive no numerical gap against the current solution.
