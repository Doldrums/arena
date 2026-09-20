# Observer evidence fixtures

These are recorded outputs of upstream unit-test fixtures at SCiEL commit
`0d67f813dd4ac21dee304f2b0de0b0ce59bf4157`. Providers and evaluation leaves were
local fakes; no model API, Docker tool or generated candidate was executed.

`terminal_decision` comes from `test_dashboard_terminal_decision.closed_cell`.
`replayed_llm` comes from `test_dashboard_parallel_replayed_llm.replayed`.
`followup_evaluated` and `followup_eval_failed` come from
`test_dashboard_research_cells_detail.followup_fixture`. The small input/alias
JSON files preserve the original synthetic target and novelty contracts.
`dashboard_v18_zero_observations.json` is the pinned upstream historical observation
fixture used to distinguish invalid penalties from valid zero measurements.

`view.json` supplies the checkpoint/events or authorization formerly returned
by each constructor. Tests copy the evidence to their own temporary directory,
then exercise observer authentication and tampering cases without SCiEL installed.

Original journal bytes, hashes, source strings and inert runtime metadata are
retained so the verification tests check the same evidence as upstream. Historical
fixture paths are evidence strings, not paths the observer is allowed to execute.

The unbound original artifact-directory label in the historical v18 fixture and
the fake-run runtime hostname are sanitized. The replayed fixture retains its
original local capacity/checkpoint path strings inside hashed journal/protocol
evidence; these are inert test-generation metadata, not runtime dependencies.
No API credential or authentication secret is included. The `authorization`
object is a synthetic provider-recovery decision, not an access token.
