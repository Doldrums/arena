# Framework integration validation — 2026-09-21

The native adapter implementation and local release contract are checked in the
working tree. This report records implementation validation, not research
performance or readiness of a deployed worker.

## Coverage

The [coverage audit](framework-coverage-20260921.md) accounts for all 99
participant records: 62 have a linked native source interface, three have
artifact-only coverage and 34 have a recorded implementation or integration
blocker. Multiple papers can share an engine; independent implementations keep
their actual authorship and repository identity.

There are 61 source-verified recipe engines with 71 launch profiles, plus three
direct adapters: 64 native interfaces and 74 profiles in total. Two additional
recipe interfaces support artifact evaluation. Original-author FunSearch is
included separately from the later corpus reimplementation. These counts do
not imply that all engines accept every catalog task.

Native launch plans bind source revisions, inspected source bytes, explicit
inputs, interpreter identities and recipe versions. Result inspection excludes
unchanged artifacts already present before launch. Review regressions cover
recursive artifact matching, abbreviated fixed-argument overrides, recipe
identity changes and Git checkout newline conversion.

## Checks

- Python suite: **1,162 passed, two skipped, 114 subtests passed**. The specialized
  source and original FunSearch checks used the locally fetched pinned sources.
- Web suite: **273 passed**; Worker API suite: **eight passed**; TypeScript check
  passed. Contribution dialog checks cover task/system flows and the email draft.
- Registry, participant snapshot, public release records and coverage report
  validation passed. No registration or validation step launches an experiment.
- Cloudflare deployment dry run passed; the Python wheel contains the runtime,
  drivers, manifests and new contribution/branding assets.
- CPIL's supplied PNG matches the served file byte-for-byte; the MBZUAI mark
  matches the official avatar package. The request-key recipient is
  `arina.kharlamova@mbzuai.ac.ae`.

Tests use controlled fixtures, fake provider APIs and source inspection. No
model-driven research loop, paid API call or hardware-dependent native run was
performed for this integration validation. The separate
[offline evaluator bridge check](framework-conformance-20260921.md) covers the
documented SCiEL/Shinka task cases only.

## Remaining deployment work

The [private release contract](../docs/private-releases.md) keeps the public PR
to a system/version reference and resolves immutable private source/image pins
inside the worker. Container dispatch, CI build attestation, cloud scheduling
and access-key issuance are not implemented by that resolver. Native dependency
environments and complete run conformance remain profile-specific. The registry
therefore does not present these interfaces as completed end-to-end integrations.

The contribution form opens a draft in the user's email application; it neither
sends mail automatically nor grants a key. Merging a version PR never starts a
run.
