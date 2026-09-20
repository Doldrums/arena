# Milestone 1 — independent Arena foundation

Implemented 2026-09-20. Arena owns its repository and UI. The old SCiEL checkout is not required to install or run the catalog. Native SCiEL results remain in their existing directories and are read through the extracted observer.

Delivered: task/participant registry and offline validation, 1,138 metadata records, source I/O declarations for 710 executable definitions, PR entrypoints, original board style and native experiment views, installable Python package, Cloudflare catalog Worker with Access verification, and CI. All participant runner adapters remain declared but unimplemented.

Local verification on the extracted project:

- Python: 509 passed, 2 skipped (unavailable historical local acceptance archives), 109 subtests passed.
- Browser DOM: 214 passed.
- Worker/API/authentication: 5 passed; TypeScript check and Wrangler dry-run passed.
- Built wheel installed in a clean environment outside the checkout with no SCiEL package; catalog, participants, health, assets and native board routes returned successfully.
- Chromium: desktop and mobile catalog/detail/participants; native board against four existing SCiEL runs, population and workflow. No JavaScript or CSP errors in the final pass.
- All 12 original native CSS files match the pinned extraction source. New catalog styles extend that baseline.

The Cloudflare Worker currently serves catalog metadata, not ingested experiments. D1/R2, Vast supervisor, native framework execution and canonical comparison remain the next implementation slice. No cloud deployment or paid experiment was performed.
