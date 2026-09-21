# Recorded results

The private board is available at `/results`, using the same tab-session access
key as `/queue`. The page only reads data: opening it, changing a filter or
refreshing never submits work or imports a participant implementation.

`GET /api/control/results` requires `read` scope. Ordinary keys see their owner's
runs; administrators see all runs. The response contains at most the newest 500
records and explicitly reports truncation. Each artifact reader is bounded and
rejects symbolic links. No candidate code, engine source, model response or
credential is returned.

SCiEL private-image runs are selected initially. Summary cards show model
coverage, classified candidate validity, distinct valid programs and the
configured native search budget. Program counts deduplicate SHA-256 identities
across the visible runs, including the initial program. Process completion and
candidate validity are separate measurements.

Canonical scores require matching evaluator receipts, candidate hashes and native
evaluation artifacts. Aggregation requires one task, source commit, problem,
evaluator, metric, direction, protocol and execution environment. A comparison
cohort additionally requires an immutable evaluator image. The initial reference
is the first recorded evaluation, not the first successful evaluation after
discarding failures. Missing or rejected records can make that reference unknown.

Native framework metrics retain their own task and scoring convention. They
never enter the canonical comparison plot. Multi-objective outcomes must keep
their dimensions rather than acquiring an invented overall score.

The resource plot pairs canonical scores with recorded wall time or complete
inspected provider-ledger token counts. It is descriptive: models, search budgets
and protocols can differ. Tokens are not dollars. Native price estimates are not
billing records, so dollar cost stays unknown. SCiEL's `B_evals` is its native
search budget, distinct from provider requests and canonical receipt counts.

Failed runs retain verified results produced before the process stopped. Missing
measurements stay unknown. These small integration pilots do not establish a
paper reproduction or a general method ranking.
