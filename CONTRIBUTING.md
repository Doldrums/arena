# Contributing

[Code style](#code-style) · [Tasks](#tasks) · [Participants](#participants) · [Private releases](#private-engine-releases) · [Checks](#checks)

Use a branch and a pull request against `main`. Existing collaborators can push a branch to this repository; external contributors can use a fork. Include the concrete behavior changed and the relevant validation. Use concise Conventional Commits, for example `fix: preserve evaluator provenance`.

Opening or merging a PR does not authorize an experiment. Execution requires a separately approved run configuration and a scoped worker key.

## Repository rules

- Source, tests and configuration files must contain at most 500 physical lines. Split by responsibility; do not compress formatting to meet the limit.
- Generated registry data, reviewed fixture data and dependency lockfiles have explicit exceptions in `scripts/check_repository_policy.py`.
- The only Markdown files are root `README.md` and `CONTRIBUTING.md`. Keep working notes, reports and run outputs outside the repository.
- Keep secrets, private bindings, local configuration, credentials and raw run archives outside the source tree. `.gitignore` restricts accepted top-level paths; CI also checks tracked files.
- Preserve the read-only observer boundary. Registry validation, imports and page loads must not run engines, evaluators or paid model calls.
- Compare results only within compatible evaluator contracts and budgets. Retain model identity, provenance and missing values in the underlying records.

Run the relevant checks listed in [README](README.md#validation). Changes to a shared boundary require its integration tests. Do not replace execution evidence with source inspection or fixture-only results.

## Code style

Apply these rules to new and changed code. Keep formatting changes scoped to the code being edited.

### Structure and readability

- Keep source, test and configuration files within **500 physical lines**. Extract modules by responsibility; keep normal whitespace and readable expressions.
- Prefer named functions and explicit imports. Put shared contracts in a dependency that both callers can import without a cycle.
- Preserve public APIs and CLI entry points when splitting modules. Use explicit re-exports where compatibility is needed.
- Name values for what they represent. Include units in resource and timing names, such as `elapsed_seconds` or `max_bytes`.
- Comments explain a constraint, decision or non-obvious behavior. Keep task history, progress notes and commented-out implementations out of source files.

### Python

- Use four spaces, `snake_case` for functions and variables, `PascalCase` for classes and `UPPER_SNAKE_CASE` for constants.
- Separate standard-library, third-party and project imports. Avoid wildcard imports and import-time filesystem, network or process work.
- Annotate new public interfaces, including return values. Keep serialization and validation at explicit boundaries.
- Catch the errors the caller can handle. Preserve unexpected failures for diagnosis; HTTP errors must not expose secrets, raw subprocess output or private paths.
- Use context managers for files and locks, and explicit cleanup for subprocesses, timers and subscriptions.

### JavaScript and TypeScript

- Use ES modules, two spaces, semicolons, `camelCase` for functions and variables, and `PascalCase` for types and classes. Match the surrounding file's quote style and preserve existing API field names.
- Prefer `const`; use `let` when reassignment is required. Validate external JSON before treating it as an application type.
- Keep TypeScript strict checks enabled. Use `unknown` and narrowing at untrusted boundaries rather than suppressing errors with `any`.
- Make UI state ownership explicit. Dispose listeners, streams and timers when their view is destroyed; ignore stale responses after navigation.
- Use `textContent` for plain text and the existing escaping helpers when constructing HTML from data.

### HTML, CSS and data

- Use semantic elements, labelled controls and visible keyboard focus. Preserve loading, empty, error and reduced-motion states.
- Use the existing CSS variables and feature stylesheets. Keep selectors scoped and preserve cascade order when extracting styles.
- Write readable CSS with one declaration per line. Use two-space indentation for CSS, JSON and YAML.
- Edit source metadata and regenerate derived catalogs with the existing scripts. Preserve source revisions, metric directions and missing values.

### Review and enforcement

CI enforces the repository layout, file-size policy, TypeScript checks, tests and builds. Formatting and module boundaries are reviewed manually; this repository has no configured Ruff, Black, ESLint or Prettier gate.

For a code change, run the relevant checks from [Checks](#checks). Tests should exercise observable behavior and meaningful failure cases. Refactors must preserve existing behavior; new performance caches need invalidation coverage. UI changes need a visual check at desktop and mobile widths.

## Tasks

A task collection registration belongs in `registry/task-sources/` and pins a full source commit. Generated task metadata is committed in `registry/catalog.json`. Catalog records retain the original source path, hash, contract, metric direction and requirements.

To update the collection, rebuild from the source checkout matching its registration:

```sh
python scripts/sync_task_catalog.py /path/to/task-source
python scripts/build_insights.py
python scripts/build_search_families.py
python scripts/build_references.py /path/to/task-source
python -m arena.registry validate
python -m arena.references validate
```

The importer reads the exact registered Git revision. It does not fetch, install dependencies or execute tasks. A new collection also needs importer and merge support; adding a registration alone is insufficient. Review the generated metadata together with the source pin.

An evaluator declaration is not a completed conformance run. Where evaluation is not yet defined, retain the source status and describe the scientific task without inventing validation or historical claims.

## Participants

Include the research paper, authors or research group, implementation URL, immutable source revision and supported native profiles. Literature-only entries remain valid research records; distinguish them from runnable integrations.

Pinned declarations live in `registry/participants/`. Launch recipes live in `registry/framework-recipes/`; direct integrations live in `src/arena/frameworks/`. Each profile must specify its actual interface and artifact contract. State environment requirements and recorded blockers explicitly. Do not infer task compatibility from a paper's claims.

```sh
python -m arena.registry validate
python scripts/audit_framework_coverage.py --check
python -m arena.frameworks --help
```

The coverage command joins every participant to native interfaces, artifact interfaces or an explicit recorded blocker. `--json` emits the inventory; `--output /path/to/inventory.json` writes it outside the default source workflow.

## Private engine releases

Keep the engine repository and container image private. The public PR contains only a version reference at `registry/releases/SYSTEM/VERSION.json`:

```json
{"schema":"arena.release/1","system":"sciel","version":"1.0.4"}
```

This is an example version, not an assertion that it is registered. Additional fields, private repository addresses and image pointers are rejected in the public record.

1. Build and test the engine in private CI from an exact source commit. Pin the resulting image by its full SHA-256 digest.
2. Register the private binding in the worker's private release store. Use the shape in `examples/releases/` and `schemas/private-release.schema.json`.
3. Open the Arena PR with the public system/version record. The reviewer verifies the private CI registration separately.
4. After review, an authorized operator selects the released version in an explicit run configuration with a task/profile, model, budget and resource limits.

Private registration:

```sh
python -m arena.releases register /srv/worker/private-binding.json \
  --store /srv/worker/releases --public-root /srv/arena-web
python scripts/check_releases.py
```

The first command prints only the public reference. The store must be private and outside the checkout and publication roots. Existing versions are immutable: changing either pin requires a new version. `resolve` is a worker-only operation whose output contains private pointers; never put it in public CI logs or PRs.

Image/source provenance must be verified by private CI. Registration validates the contract and pins, but does not prove the build, execute the image or grant permission to run it.

## Experiment results

Keep native logs and evidence immutable outside the repository. Inspect them with `python -m arena --root /path/to/archives`. Publish through the explicit results exporter after verifying artifact identities, evaluator contracts and accounting coverage.

Results should expose scores, budgets, elapsed time, measured calls and recorded changes to research cells or tools where available. Report the denominator and evidence source. Do not fill missing measurements, combine incompatible protocols or turn an observed association into a causal RSI claim.

Changes to published snapshots and deployments require review independently of engine version registration.

## Running the services

The local read-only board starts with `python -m arena`. It defaults to `outputs/` and `autoresearch/`; repeat `--root` to select other archive directories. The service binds to loopback. Installed wheels include the interface, registry and schemas.

### Private control and workers

`examples/control.json` describes the configuration shape. Replace its placeholders in a private configuration file outside the repository.

```sh
python -m arena.control check --config /srv/arena/control.json
python -m arena.control serve --config /srv/arena/control.json
python -m arena.control worker --config /srv/arena/control.json --concurrency 4
```

The worker command executes authorized queue entries. Provision Linux isolation, cgroups, root-owned brokers, model credentials and resource limits before starting it. Choose concurrency according to evaluator CPU/RAM requirements and provider quotas. Deployment units and setup commands are in `scripts/deployment/`.

Use `python -m arena.control create-key --help` for scoped credentials and quotas. Treat its output as a secret. Execution access is separate from Cloudflare sign-in; request it through the board or [arina.kharlamova@mbzuai.ac.ae](mailto:arina.kharlamova@mbzuai.ac.ae).

### Cloudflare development and deployment

Requires Node 22.12+:

```sh
npm ci
npm run dev:cloudflare
```

The local Worker listens at <http://127.0.0.1:8788>. Production uses `api/src/index.ts` and verifies Cloudflare Access identities before serving assets or API responses. `ACCESS_TEAM_DOMAIN` and `ACCESS_AUD` must match the Access application. The configured login policy allows `mbzuai.ac.ae` addresses and explicitly approved users.

`OBSERVER` is an optional VPC Service binding to a private loopback observer. Only allowlisted GET/HEAD routes and bounded event streams are forwarded. Queue/control APIs and mutations are unavailable through this Worker. Without the binding, native experiment routes report unavailability.

```sh
npm run check:cloudflare
npx wrangler deploy --keep-vars
```

The first command builds without deploying. Verify the Access application and observer binding before deployment; preserve existing Access variables and keep preview URLs disabled.

The deployed observer can use a separately pinned release through the `arena-board.service` systemd `PYTHONPATH` override. Update that override when upgrading the board. An observer-only release does not require restarting the experiment worker. Keep run archives, imported snapshots and private release bindings outside static publication roots.

### Publishing results

The discovery Results page reads `registry/results-overview.json`; refresh reloads that published snapshot. Publish new measurements with an explicit export, review and deployment. The workspace uses the published overview when its private control API is unavailable.

```sh
python scripts/export_results_overview.py --help
```

The exporter accepts a private results response, optionally with a validated research section. Updating an existing published snapshot requires a separate validated research section. It does not collect credentials or launch runs. Review the exported evidence, evaluator groups and accounting coverage before deployment.

## Checks

After installing the development dependencies from [README](README.md#validation):

```sh
python scripts/check_repository_policy.py
python -m arena.registry validate
python scripts/check_releases.py
python scripts/audit_framework_coverage.py --check
python scripts/build_insights.py --check
python scripts/build_search_families.py --check
python -m arena.references validate
python -m pytest -q
npm run test:web
npm run test:api
npm run typecheck
npm run check:cloudflare
python -m pip wheel . --no-deps -w dist
```

These default checks do not launch paid model calls or research runs. Linux VM conformance requires an explicitly enabled environment; fixture tests do not establish deployment readiness.
