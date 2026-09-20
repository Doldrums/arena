# Effort comparison UI verification

Passed on an ephemeral loopback Arena observer (`127.0.0.1:58346`) reading the existing Circle Opus V32, Heilbronn V32 and oracle V32 directories. All three had already been paused by the coordinating restart; the page correctly showed Paused. No experiment, saved program, evaluator, research tool or provider was executed. Existing dashboard ports were not changed.

Desktop 1440×1100 and mobile 390×844 checks passed for all three tasks: no JS errors or missing assets, no document overflow, and no clipped effort/model disclosures or headline comparison text. The reference table scrolls horizontally on mobile. Screenshots were visually inspected.

Circle current row binds p29 to the native value 2.6359830849122936. Its receipt cutoff is 16:52:53.042623 UTC: $3.473920, 15 completed LLM calls, 9 program evaluations and 15m51s elapsed; the saved owning evolution iteration is 1. The separate current total was $11.209515 and 54 completed calls. The table preserves different-tolerance separation and the Best known / Best AI search headline gaps.

Expanded Shinka provenance shows all six configured LLM identities and their roles, the separate embedding model, protocol caveat and primary-source link/locator. Theta's derived sample count and derivation have DOM coverage. Unknown published dollars/calls/CPU remain unknown. The observer cannot price CPU or prove equal discovery budgets.

The first screenshots caught inherited nowrap clipping in the reference headline and expanded descriptions. These were corrected with scoped wrapping and table widths. Preliminary evidence remains in `attempt1/` and `attempt2/`; the root-level PNGs and `live-ui.json` are the final check. `verify_ui.cjs` is the reproduction script, using an already-started ephemeral server identified by `/tmp/arena-effort-qa-server.json`.

Validation: focused Python 200 passed, 1 skipped, 47 subtests; full web suite 259 passed before final presentation polish; final effort/dashboard DOM checks 29 passed. The temporary observer was stopped after this check.
