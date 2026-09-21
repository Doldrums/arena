# Empira

Empira is a research arena for systems that improve their own search, code or learning procedures. It brings together scientific task definitions, framework registrations, recorded experiments and resource accounting. Research-cell and tool activity are observable process measurements; they do not by themselves establish recursive improvement.

The Python package and operational commands use the name `arena`.

## Architecture

| Component | Responsibility |
| --- | --- |
| `web/` | Task catalog, participants, results and the experiment workspace |
| `api/` | Cloudflare Access verification, published snapshots and private observer routing |
| `src/arena/observers/sciel/` | Read-only journal, checkpoint and heartbeat interpretation |
| `src/arena/frameworks/` | Pinned framework profiles and explicit launch interfaces |
| `src/arena/control*` | Authenticated queue, quotas, worker leases and cancellation |
| `src/arena/*proxy*`, `engine_broker*` | Private execution boundaries and bounded evaluator access |
| `registry/`, `schemas/` | Versioned task, participant, release and comparison contracts |

Frameworks retain their own search algorithms and state. The observer does not import the SCiEL engine or execute code from a run archive. A page load, registry update or PR cannot start an experiment.

A registered paper, a source-verified launch interface, a prepared environment and a successful evaluation are separate states. Recipe metadata records their scope and remaining requirements. Continuous task/system discovery is a separate integration under development.

## Local board

Requires Python 3.11+:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m arena --root /absolute/path/to/run-archives
```

The server listens at <http://127.0.0.1:8787>. Repeat `--root` to observe multiple directories. Without this option, it checks local `outputs/` and `autoresearch/`. No SCiEL installation is needed to inspect saved runs.

| Route | View |
| --- | --- |
| `/` | Task atlas, research domains and catalog |
| `/?view=participants` | Research systems, authors and source papers |
| `/results` | Published research results |
| `/experiments` | Native experiment details |
| `/experiments/results` | Results within the workspace sidebar |
| `/experiments/queue` | Queue, when connected to an authorized private control API |

Results group runs by evaluator contract and model. Published references, measured runs and integration checks remain distinct. Missing accounting stays missing; activity counts and best observed results are not evidence of causal improvement or an unmeasured speedup.

## Cloudflare

Requires Node 22.12+:

```sh
npm ci
npm run dev:cloudflare
```

The local Worker listens at <http://127.0.0.1:8788>. Production uses `api/src/index.ts`; every asset and API request requires a verified Cloudflare Access identity. `ACCESS_TEAM_DOMAIN` and `ACCESS_AUD` must match the Access application. The current sign-in policy allows `mbzuai.ac.ae` addresses and explicitly approved users.

`OBSERVER` is an optional VPC Service binding to a private loopback observer. Only allowlisted GET/HEAD routes and bounded event streams are forwarded. Queue/control APIs and mutations are not exposed through this Worker. Without the binding, native experiment routes report unavailability.

The discovery results page reads `registry/results-overview.json`; refresh reloads that published snapshot. Publishing new measurements requires an explicit snapshot export and deployment. Use `python scripts/export_results_overview.py --help` for source and filtering options.

```sh
npm run check:cloudflare
npx wrangler deploy --keep-vars
```

The first command builds without deploying. Before a production deployment, verify Access configuration and the observer binding. Preserve existing Access variables and keep preview URLs disabled. Deployment units and VM setup commands are in `scripts/deployment/`.

The deployed observer can use a separately pinned release through the `arena-board.service` systemd `PYTHONPATH` override. Update that override when upgrading the board; restarting the experiment worker is unnecessary for an observer-only change. Keep run archives, imported snapshots, credentials and private release bindings outside static publication roots.

## Private execution

`examples/control.json` describes the configuration shape. Replace its placeholders in a private configuration file; it is not a ready-to-run deployment.

```sh
python -m arena.control check --config /srv/arena/control.json
python -m arena.control serve --config /srv/arena/control.json
python -m arena.control worker --config /srv/arena/control.json --concurrency 4
```

The worker command executes authorized queue entries. Provision the Linux isolation, cgroups, root-owned brokers, model credentials and resource limits before starting it. Concurrency must fit evaluator CPU/RAM requirements and provider quotas; a launch profile alone does not prove capacity.

Use `python -m arena.control create-key --help` for scoped credentials and quotas. Treat its output as a secret. The board's request form contacts [arina.kharlamova@mbzuai.ac.ae](mailto:arina.kharlamova@mbzuai.ac.ae) for access; this is separate from Cloudflare sign-in.

Private engines can remain in private repositories and images. A public version reference resolves to immutable worker-only source/image pins; see [contributing](CONTRIBUTING.md#private-engine-releases).

## Validation

```sh
python scripts/check_repository_policy.py
python -m arena.registry validate
python scripts/check_releases.py
python scripts/audit_framework_coverage.py --check
python scripts/build_insights.py --check
python scripts/build_search_families.py --check
python -m arena.references validate
python -m pytest -q
npm ci --prefix tests/web
npm run test:web
npm run test:api
npm run typecheck
npm run check:cloudflare
python -m pip wheel . --no-deps -w dist
```

Default checks use fixtures and local transports. They do not launch paid model calls or research runs. Linux VM conformance requires its explicit opt-in environment; passing local tests does not certify that deployment. Wheels bundle the UI, registry and schemas.

## Attribution and licensing

The observer and experiment UI originate from the private `Doldrums/sciel` repository. Baseline file hashes are preserved in `registry/provenance/sciel-extraction.json`. This repository grants no new open-source license to that material.

Task metadata derives from `IMRUNya/autoresearch-tasks` at the immutable revision in `registry/task-sources/autoresearch-tasks.json`. External implementations, datasets and evaluators retain their original terms. A participant declaration does not relicense its source code.

The [CPIL mark](https://cpil-lab.github.io/images/brand/cpil-lab-concept.png) and the MBZUAI avatar from its [official media package](https://staticcdn.mbzuai.ac.ae/mbzuaiwpprd01/2026/02/MBZUAI-Avatars.zip) were retrieved unchanged on 2026-09-21. The marks belong to their respective organizations. SF Pro resolves from local installation; no font binaries are distributed.
