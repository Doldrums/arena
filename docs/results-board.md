# Recorded results

The landing Results tab at `/results` opens a compact published overview without
an experiment access key. Numeric tables show SCiEL research observations and
integration outcomes, followed by a score/resource chart within one evaluator
cohort, experiment coverage and a short expandable system table.
The timestamp explicitly identifies the published snapshot; this is not a live
queue. The existing “Follow the research behind the numbers” panel leads to the
full experiment workspace. Production Cloudflare team Access still applies.

`GET /api/results-overview` serves only the reviewed `registry/results-overview.json`
snapshot in both the Python board and Cloudflare catalog. It never accesses the
control service or falls back to private run data. The export excludes run IDs,
user labels, owners, private versions, paths, artifacts, source hashes and prompts.
It preserves failed and cancelled runs, unknown measurements, and evaluator
cohort boundaries. Program counts include the initial programs (seeds).

An operator refreshes the snapshot from an authenticated results response saved
outside the repository:

```sh
python3 scripts/export_results_overview.py --input /private/results.json --research-input /private/research-section.json --output registry/results-overview.json
```

Review and deploy the aggregate with the catalog. Never commit the private input
or its access key. The export is offline and performs no model calls or launches.

The optional research input is a validated public-safe projection produced by
`arena.results_research.build_results_research` from native observer records.
It contains no code, prompts, private run identifiers or paths. Research protocols
remain separate from each other and from the integration evaluator cohorts.
The best-per-model view shows the selected run's own initial score, best score,
status and elapsed time, alongside the number of recorded runs for that model.
Elapsed time includes pauses; it is not compute time or a billing measurement.
The alternative view lists every recorded research run. Native integration
metrics retain their scoring conventions and paired multi-objective values.

The experiment workspace retains its left sidebar: Experiments at `/experiments`,
detailed Results at `/experiments/results`, and Queue at `/experiments/queue`.
`/queue` remains an alias. Landing Results always shows the published overview,
including when a key is saved locally. “Open experiment board” leads to the
owner-scoped detailed workspace, where the experiment key is used.
Opening pages, changing filters or refreshing never submits work.

`GET /api/control/results` requires `read` scope. Ordinary keys see their owner's
runs; administrators see all runs. The response contains at most the newest 500
records and explicitly reports truncation. Each artifact reader is bounded and
rejects symbolic links. No candidate code, engine source, model response or
credential is returned.

SCiEL private-image runs are selected initially; other systems and all systems
are available in the system filter. Model, status, native budget and search filters
apply to the summaries and table. The task/evaluator selector applies only to the
two score plots. Best-score sorting is enabled only for one canonical cohort with
recorded scores; native outcomes never acquire a cross-task ranking.

Summary cards show run and model coverage, classified candidate validity,
distinct valid programs, median recorded tokens and process completion. Program
counts deduplicate SHA-256 identities across filtered runs, including the initial
program. The token median includes ended runs with complete inspected ledgers;
partial usage stays visible in bars and the table. Process completion and candidate
validity are separate measurements. Inspect reveals native outcomes, native budget,
provider requests, evidence identities and paired multi-objective measurements.

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
and protocols can differ. The observed frontier marks non-dominated measurements
among ended runs with fully recorded canonical evidence; the token axis also
requires complete ledgers. A scoped annotation identifies the lowest recorded
resource use at the best observed score, without claiming general superiority.
Seed/best plots show endpoints only, not a convergence trajectory. Tokens are not dollars. Native price estimates are not
billing records, so dollar cost stays unknown. SCiEL's `B_evals` is its native
search budget, distinct from provider requests and canonical receipt counts.

Failed runs retain verified results produced before the process stopped. Missing
measurements stay unknown. These small integration pilots do not establish a
paper reproduction or a general method ranking.
