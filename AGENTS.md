# Arena implementation

- Arena owns its catalog, registry, environments, run lifecycle and board. Frameworks remain external participants.
- Preserve the extracted SCiEL board style; build catalog and management views from its existing visual patterns.
- `src/arena/observers/sciel` is read-only and must not import SCiEL Engine or execute user code. Preserve native schema names and provenance semantics.
- Registry changes pin immutable commits. Registration, built environments, conformance and runnable adapters are separate states.
- Page loads, validation, PR checks and registry updates must not launch paid experiments.
- Run appropriate local Python/DOM/Worker checks. Do not deploy resources as a side effect of tests.
- Production must protect both static assets and API with verified team Access tokens.
