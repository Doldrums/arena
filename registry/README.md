# Registry

This directory is the versioned, team-curated registration source for the independent Arena. Changes enter through a PR in [Doldrums/arena](https://github.com/Doldrums/arena). Private task repositories are supported by the intended GitHub App model; v1 reads a reviewed local snapshot and does not contact GitHub at runtime.

- `task-sources/*.json`: repository registrations pinned to a full commit SHA.
- `participants/*.json`: pinned external framework declarations. All three native adapters are currently **not implemented**.
- `catalog.json`: endpoint-ready metadata for 1,138 task packages; 710 declare executable evaluators, 428 explicitly do not. No runtime, dependency, GPU, dataset or service availability is inferred from those declarations.
- `participants.json`: endpoint-ready aggregate of participant declarations.

The snapshot contains allowlisted catalog metadata, declared input/output contract prose from each pinned `problem.json`, source URLs, limitations and original source-file SHA256 values. `contract_source` records that file's exact GitHub blob URL and digest. This revision contains 710 declared contracts; all 428 unsupported tasks leave `contract` null. These contracts are source declarations, not Arena conformance evidence. The snapshot includes no evaluator code, commands, environment-variable values, credentials, local run directories or imported experiment results. A task package is not necessarily an independent scientific problem; the same benchmark can occur under several paper protocols.

Validate offline:

```sh
PYTHONPATH=src python3 -m arena.registry validate
```

Rebuild from an already available source checkout, reading the exact Git objects named by the registration:

```sh
python3 scripts/sync_task_catalog.py /path/to/autoresearch-tasks
```

The command never fetches repositories, installs dependencies or executes tasks. This initial importer supports the single `autoresearch-tasks` collection. It refuses additional source registrations before writing anything; additive multi-source synchronization is not implemented yet. Adding a second task collection requires implementing its importer and merge rules in the same PR, rather than replacing the existing catalog. Review generated output together with `task-sources/autoresearch-tasks.json` in the registry PR. `catalog.json` and `participants.json` use the same response shape in the Python API and the Cloudflare API. JSON Schemas live in `schemas/`; additional cross-record/status invariants are checked by the stdlib validator.

Six prompt-optimization task records contain different dependency declarations in the source `catalog/tasks.json` and `suite/index.json`. The snapshot preserves the catalog's requirements and records the alternate index requirements and an explanatory note in task provenance. The difference does not establish runtime availability.

Remote refresh, GitHub App provisioning, webhook processing, image builds, conformance execution, native framework runners and canonical evaluation services remain planned. Source `validation_level` and `upstream_reproduction` fields retain the library author's assertions and are not independent Arena certifications.
