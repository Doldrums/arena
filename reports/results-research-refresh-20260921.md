# Research-first Results update — 21 September 2026

Results previously led with integration counters and a SAT comparison where the
recorded initial and best scores were equal. The stronger SCiEL research outcomes
were confined to a lower table. This update puts measured research quality,
recorded time to best and outcomes across models first, using the existing
neutral Arena visual language and amber data accents.

The discovery Results page and the workspace Results page share the published
research dashboard. The workspace keeps its sidebar. Without an available
private control API, it shows published results instead of an empty key prompt;
an authenticated private control view still preserves its existing filters and
run inspection. Published requests never receive a control key.

## Data and comparison scope

The research snapshot was refreshed from the 203 imported native runs: 145 circle
packing, 29 oracle and 29 Heilbronn runs. All 203 have measured outcomes; 197
improved their own measured initial solution. Six exact task/metric protocol
groups remain separate. The canonical integration section is unchanged: 196
runs and 32 system profiles retain their original source timestamp.

The default circle-packing group contains 80 recorded runs across five model
configurations: 74 improved their starting solution. Its best recorded sum of
radii is 2.6359830849122985, reached at 839.151671 seconds by GPT-6 Astra. The best
recorded endpoint reached within five minutes is 2.6359830797175117 at 290.591699
seconds, also GPT-6 Astra. These are descriptive measurements, not a claim of
superiority over other frameworks or an estimate from independent repeats.

The time selector chooses each run's final recorded best when that endpoint was
reached within the selected elapsed time. It does not reconstruct earlier
trajectory points or evaluate every run at a common fixed budget. Pauses are
included in elapsed time. The plots retain all measured outcomes, provide a
single-model filter and identify the observed endpoint frontier and per-model
median. Best-per-model table rows preserve the initial score and elapsed time of
the same selected run; every recorded row is also available.

165 research rows have a complete physical-receipt token ledger; 112 identify
subscription billing without a supplied USD price. Optional public usage fields
have a strict allowlist and preserve total-run scope. They are not attributed to
time-to-best and are not converted into invented dollar costs. Incomplete token
records stay unknown. Private paths, raw artifacts and run IDs are not published.

## Implementation and validation

- Pure research analytics reject mixed evaluator contracts and handle metric
  direction, missing values, exact ties and recorded elapsed checkpoints.
- Python publication validation: 97 tests passed.
- Python static/public route checks: 11 tests and 49 subtests passed; includes
  the new helper asset and aggregate access independent of control authorization.
- Results DOM and analytic suites: 85 tests passed, covering published/private
  transitions, model/checkpoint filtering, distribution coverage, partial tokens,
  keyboard focus and retained integration evidence.
- Worker publication/privacy check and TypeScript checks passed.
- Chromium checks rendered both Results routes at 1440px and 390px with no page
  overflow or browser errors, and exercised model filters, elapsed checkpoints
  and the integration disclosure. The workspace sidebar remains intact.

No experiment was launched or resumed. The deployment updates only the board and
its published snapshot; execution controls remain behind their existing boundary.
