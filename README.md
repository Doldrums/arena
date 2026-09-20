# Empira

Empira is a living research arena for AI agents learning from experience. It is being built to study how experiments, accumulated evidence and revised research methods change what a system does next. The name evokes empirical knowledge; the Python package, API and repository retain the technical name `arena`.

Arena owns tasks, environments, participant registration, experiment records and comparison. Frameworks own their learning, search algorithms and state: SCiEL, ShinkaEvolve and Darwin Gödel Machine remain separate repositories. New task and system versions enter through reviewed, versioned contributions.

The current release provides a task catalog, participant registry and independent experiment observer. Continuous discovery and parsing of tasks and RSI/self-improving research systems are being developed in a separate coauthor workstream and will be merged later; that integration is incoming. See [the product positioning](docs/positioning.md) for the connection to the Era of Experience and the distinction between current capabilities and intended development.

The board keeps the native SCiEL experiment views inside an independent Arena shell. Its visual system uses SF Pro Text, soft widget cards and an interactive research landscape. Experiments has a separate neutral treatment: white cards, gray controls, dark type and color reserved for statuses and data. SF Pro Text resolves from a local installation; system sans-serif is the fallback. Font binaries are not redistributed.

## Working now

- Task catalog: **1,138 task packages**, searchable by name/content and filterable by family and protocol. Task details expose available source input/output contracts, metrics, requirements and pinned provenance; missing contracts remain explicit.
- Research landscape: one point per task, with a **Search methods / Task families** switch, hover isolation, pinned selection and catalog drill-down. Search-method groups reflect source-paper associations, not measured framework compatibility or solved results. See [the source mapping](registry/SEARCH_FAMILIES.md).
- Scientific overview: equal-size research-direction cards with questions and real task examples; exact domain shares and evaluator coverage are available under Corpus composition. Task-type distributions and source-bound reference/seed evidence remain accessible. Charts drill down into the task catalog. See [what the statistics mean](docs/task-overview.md).
- GitHub registry: **three participant declarations** (SCiEL, ShinkaEvolve, DGM), immutable source revisions, JSON schemas, offline validation and PR templates.
- Independent SCiEL observer: existing experiment, source/diff, population, workflow, LLM accounting, research cells/tools and packing views. It reads saved journals and live heartbeat files; it does not import SCiEL Engine.
- Cloudflare Worker: the same catalog and static UI, with verified Cloudflare Access tokens required in production. Local development is available without cloud credentials.

**710 packages declare an executable evaluation protocol; 428 are unsupported.** That is upstream catalog metadata, not a claim that 710 tasks have passed Arena conformance. No framework launch adapter is integrated yet. This milestone cannot start paid experiments. The cloud Worker does not yet ingest native runs; its experiments API reports that limitation explicitly.

## Run the board locally

Python 3.11+; no SCiEL installation is required.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m arena
```

Open <http://127.0.0.1:8787>. To inspect existing SCiEL experiments without moving their data:

```sh
python -m arena --root /absolute/path/to/sciel/outputs --root /absolute/path/to/sciel/autoresearch
```

The server binds to loopback. Use `/` for the catalog, `/?view=participants` for participants, and `/experiments` for the native experiment board. An empty run list is expected when no run roots are supplied or present. Observer timing caches live outside the watched experiment directories.

## Registry changes through GitHub

Read [the registry guide](registry/README.md). Add a task collection or participant declaration in a PR, pin the full commit and regenerate the catalog snapshot when its source changes. The snapshot contains metadata; evaluator code and datasets stay in their source repositories. CI validates the registry offline and never starts an experiment.

```sh
python -m arena.registry validate
```

A registration is separate from an implemented runner, a built environment and successful conformance. The UI shows these distinctions; an upstream framework capability does not automatically become an Arena capability.

## Cloudflare development

Node 22.12+:

```sh
npm ci
npm run dev:cloudflare
```

Open <http://127.0.0.1:8788>. This local Worker serves the catalog and participant registry. Native runs require the Python observer above until the ingestion milestone.

```sh
npm run typecheck
npm run test:api
npm run check:cloudflare
```

`check:cloudflare` builds without deploying. Production uses `api/src/index.ts`, protects all assets and API routes, and fails closed until `ACCESS_TEAM_DOMAIN` and `ACCESS_AUD` are configured. A Cloudflare Access application must restrict its policy to the team. No Cloudflare resources, public routes or Vast instances are created by this repository's CI. See [deployment notes](docs/deployment.md).

## Checks

With the Python environment active:

```sh
python -m pytest -q
npm ci
npm ci --prefix tests/web
npm run test:web
npm run test:api
npm run typecheck
npm run check:cloudflare
```

The tests use synthetic fixtures, saved protocol evidence and static metadata, without paid APIs or research runs. Python wheels include the web UI and registry so the installed package does not depend on a checkout of SCiEL.

## Layout

| Path | Owns |
| --- | --- |
| `web/` | Arena catalog UI and extracted native experiment views |
| `registry/`, `schemas/` | Task sources, participants and their validated snapshots |
| `src/arena/` | Local server, registry reader and framework observers |
| `src/arena/observers/sciel/` | Read-only SCiEL journal protocol and compatibility helpers |
| `api/` | Cloudflare catalog API, Access verification and static routing |
| `tests/` | Registry, observer, browser DOM and Worker regression checks |
| `docs/` | Architecture, migration record and deployment boundaries |

## Next implementation milestones

1. D1 run state and leases, R2 immutable artifact manifests, authenticated ingestion.
2. Vast VM supervisor with pull/heartbeat/cancel, durable spool and bounded resource policies.
3. SCiEL native runner adapter and canonical evaluation for a small conformance task set.
4. ShinkaEvolve native runner adapter on the same tasks and budgets.
5. Canonical comparison board, then a separate DGM agent-bundle/episode protocol.

These are planned work, not present capabilities. The accepted system boundary and UML sources are in [the architecture RFC](docs/arena-integration-architecture.md).
