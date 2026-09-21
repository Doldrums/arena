# Model coverage and recorded search effort — 21 September 2026

## What changed

The previous model distribution followed the main evaluator filter. This exposed
five GPT model configurations while Claude Opus 5 and Gemini 2.5 Flash remained
in another evaluator group. The model panel now covers all recorded outcomes for
the selected task, with a separate scale, median and best result for each exact
metric/evaluator contract. Circle packing has 145 outcomes across seven models:
80 in one evaluator group and 65 in the other. The metrics, elapsed-time chart
and detailed table retain their selected evaluator/model scope.

The headline best-result cards emphasize SCiEL's measured result and recorded
time, rather than the generating model. Actual model identities remain available
in the distributions, run table and selected-run details.

## Selected small-call-budget observation

The selected Opus run reached a sum of radii of 2.635983084525617 after
141.136239 seconds. The native physical-receipt ledger through that result's
evaluation records four completed calls, four dispatched calls, no pending calls
and complete history. The full run later accumulated 19 calls. These scopes are
not interchangeable.

The run began fresh with the simple initial program scoring
0.9597642169962064. The four prompts contained that initial program and the task's
2.635 target; they did not contain imported inspirations, fragments, lessons,
failed hypotheses or the ShinkaEvolve score. Recorded research exchange began
after this best result. This supports a within-run observation, not a claim of
novel discovery or a count including earlier framework development.

The comparison reference is Sakana AI's reported relaxed ShinkaEvolve score,
2.635983099011548, in [Appendix B.1 of the paper](https://arxiv.org/html/2509.19349v1#A2.SS1).
Both use 26 circles in the unit square, sum of radii and slack 1e-6. The numerical
gap is approximately 1.4485931e-8. The paper's separate radius-shrunk strict score
is not used. Matching slack does not establish identical numerical verification.

The card chooses the smallest complete recorded call count among endpoints within
1e-7 of this reference and explicitly identifies the outcome as a selected run.
It does not describe the reference as today's global best. The paper reports a
150-generation campaign, not 150 total physical LLM calls; no call-efficiency
ratio, common-budget win, dollar saving or wall-time speedup is inferred. The
models and search conditions also differ.

## Evidence handling

Optional public effort-to-best counters are bound to the same recorded best
program, evaluation, source, metric display and elapsed cutoff in the operator's
private projection input. Public fields contain only the within-run counting
scope, completed/dispatched/pending calls, history completeness and elapsed time.
Private identifiers, source hashes, paths, prompts and artifacts are excluded.
Unknown or incomplete effort never qualifies for the compact highlight.

## RSI-first activity overview

The first panel now summarizes changes to the research machinery across all
203 recorded runs, independently of the score filters: 329 research-cell creation
events, 506 cell revisions, 222 authored tool versions registered and 220 with
recorded use (99.1%). There are 278 recorded executions and 358 observation
deliveries into research prompts. All 203 archived event histories are complete
and have distinct native run UUIDs.

Creation counts are summed within runs. The cell IDs are not globally unique
inventions (117 distinct IDs occur across those creations); built-in tools and
checkpoint-only inherited cells are excluded. Use requires an invoked result
with invocation and receipt references; failures still count as executions,
not successful outcomes. Artifact bodies are not independently reverified by the
aggregate. Delivery means exposure to a prompt, not measured adoption or benefit.
Counts therefore describe process changes, not causal evidence of improved scores
or a demonstrated recursive capability gain. The four-call packing example has
zero research-tool events and remains a separate initial-search efficiency result.

## Validation

- 171 Python tests and 51 route subtests passed, covering publication, effort
  identity/metric/source binding, RSI event lineage, unknown coverage, malformed
  event handling and both new static modules.
- 60 Results DOM/analytic tests passed; the separately checked final ratio note
  uses the same recorded registration/use counters.
- Worker publication/privacy check and TypeScript checks passed.
- Real-data Chromium checks on both Results routes at 1440px and 390px confirmed
  the RSI-first panel, all seven model labels and 145 circle-packing outcomes,
  four-call reference card, preserved model-filter isolation and workspace
  sidebar. No JavaScript errors or horizontal page overflow occurred.

Deployment verification will be appended after publication.
