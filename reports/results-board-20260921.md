# Results board deployment — 2026-09-21

The private `/results` page and owner-scoped `/api/control/results` endpoint
are deployed on the experiment VM. The queue key is reused within the browser
tab. Loading or refreshing this board never starts research.

The first live response contained 154 runs. SCiEL private-image records included
seven models, 44 valid canonical evaluations and 38 distinct valid program
hashes across runs. Six inspected provider ledgers had complete token coverage;
the failed Luna run retained its two valid evaluations and partial usage. Every
SCiEL run's best observed score equaled its initial score, so no improvement over
the initial program is claimed. The native search budget `B_evals=4` is shown
separately from requests, tokens and evaluator receipts.

Canonical scores are isolated by evaluator identity. Known native contracts
cover 13 framework IDs, including separate CoEvo variants; they retain task,
direction and native scope. A read-only sweep verified 72 completed native
projections. MEoH retains paired objectives; ReEvo/HSEvo expose held-out validation
metrics. An older EoH run without a native summary remains unknown.

Review corrected mixed local-evaluator aggregation, credential-shaped labels,
malformed nested JSON, modified/copied provider intents, orphan terminal receipts,
and tool operations incorrectly counted as provider requests. Failed runs remain
visible. Native price estimates are never presented as billed dollars.

Validation:

- 1,860 Python tests and 114 subtests passed; 29 environment-dependent checks skipped.
- 297 web tests passed, including 18 Results tests; real API payloads rendered in DOM checks.
- Live page and both assets returned HTTP 200; unauthenticated Results API returned 401.
- The authenticated response retained owner scope. The worker PID did not change during the board update.
- Browser pixel rendering was not performed in this pass.

Deployment proof: `/srv/arena/build/results-board-20260921/proof.json`, SHA-256
`255bd17ac1753a72df85b4eb0ebf7f673bea3e7d54bedfd555fe540dc3fb6884`.

The same reviewed change adds bounded AEL, ADAS, QDAIF, AFlow and PromptAgent
gateway profiles. Their first Sol pilots were admitted separately; offline
conformance is distinct from successful research completion. Twelve remaining
Darwinian/CoEvo model cells were admitted after their first native results were
audited. These admissions preserved `max_active=4`; the final inventory contained
231 templates. Existing experiments were not restarted.
