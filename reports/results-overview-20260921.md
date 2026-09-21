# Landing Results overview — 2026-09-21

The landing Results tab now renders a compact, explicitly published snapshot
without an experiment key. It includes four measurement cards, a cohort-specific
score/resource plot, process and evaluation coverage, and an expandable system
table. The research hand-off panel and the separate experiment sidebar remain.

The published snapshot contains 196 runs, 32 versioned system profiles and seven
models. Its timestamp is visible; it is not presented as a live queue. The export
contains no private run identifiers, user labels, engine versions, artifacts or
credentials. Failed/cancelled runs remain included; distinct programs include
seeds. Only complete token ledgers enter token medians and the token plot.

Validation: 346 web tests; 30 Python tests with 48 subtests; nine Worker API tests;
TypeScript; Cloudflare dry-run build; desktop and mobile browser inspection.
Independent review verified evaluator isolation, initial chart visibility,
keyboard focus retention and absence of credential-bearing overview requests.

The initial deployment check caught a missing static-asset allowlist entry and
rolled back. The corrected allowlist has HTTP regression coverage. The final
board deployment serves the aggregate with HTTP 200, retains HTTP 401 on private
results without a key, and preserves authenticated owner scope. The worker PID
remained unchanged; experiments were not restarted.

Deployment proof: `/srv/arena/build/results-overview-20260921/proof.json`.
