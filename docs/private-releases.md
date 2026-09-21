# Private releases

Arena can bind a public system/version reference to a worker-only Git commit and
container image digest. Registration records the binding; it never downloads
source, starts an image, evaluates a candidate or publishes a release.

This is a local release contract and resolver. Private image execution, cloud
orchestration, CI attestation verification and a RunSpec dispatcher that resolves
release references are not implemented by this module. The existing native
framework runners remain a separate interface.

## Public reference and private binding

The public record has exactly three fields, validated by
[`release.schema.json`](../schemas/release.schema.json):

```json
{"schema":"arena.release/1","system":"example-system","version":"0.0.0-example"}
```

Only `system` and `version` identify the release; `schema` selects this contract.
A value such as `system=sciel`, `version=1.0.4` would follow the same format, but
is an illustration, not a claim that such a release has been registered. Public
records reject all additional fields, including repository URLs, commit hashes,
image pointers and credential fields.

Public PRs place the record at `registry/releases/SYSTEM/VERSION.json`.
`python scripts/check_releases.py` validates its identity, location and strict
field boundary in CI without contacting the private worker. The
[participant PR template](../.github/PULL_REQUEST_TEMPLATE/participant.md)
explains both private version updates and new public integrations. This public
check cannot attest that the private binding exists; the reviewer verifies
private CI's registration separately.

The worker-only record uses
[`private-release.schema.json`](../schemas/private-release.schema.json):

```json
{
  "schema": "arena.private-release/1",
  "system": "example-system",
  "version": "0.0.0-example",
  "repository": {
    "url": "https://code.example.invalid/team/example-system",
    "commit": "0000000000000000000000000000000000000000"
  },
  "image": "registry.example.invalid/team/example-system@sha256:0000000000000000000000000000000000000000000000000000000000000000"
}
```

These `.invalid` addresses and zero hashes are nonfunctional placeholders, also
provided in [`examples/releases`](../examples/releases). Use a real full 40-digit
Git commit and an image reference pinned by a full SHA-256 digest. Branches,
moving tags, tag-plus-digest image syntax, credentials in URL user information,
URL queries and unknown fields are rejected. Authentication belongs in the
private CI/worker secret store or execution environment, never either record.

Registration of an identical binding is idempotent. Changing the repository,
commit or image for an existing system/version fails; create a new version.
Concurrent registrations use atomic create-only publication, so a version cannot
be overwritten and a resolver never sees a half-written registration. Missing,
malformed, duplicate-key, wrong-identity or unsafe private records fail closed;
there is no fallback to a branch, latest image or public repository.

## Intended workflow

1. Private CI builds and checks the image from an exact source commit. CI supplies
   the immutable binding to the worker's private release store. The contract
   validates the two pins, but does not independently prove that the image was
   built from that commit; build verification remains CI's responsibility.
2. CI's registration command returns only the public system/version reference.
   A public PR contains that reference and public review material, with no private
   repository or image pointer.
3. The PR is reviewed. Registering a version, opening a PR or accepting its public
   record does not authorize or trigger execution.
4. A separately authorized worker operation resolves the reviewed reference and
   validates an explicit RunSpec with task/profile, runtime limits, model/key
   environment names and budget. The worker keeps the private binding and
   credential values out of public plans and results. That image-running and
   orchestration step still needs an implementation.

Do not use this resolver in a public HTTP route. `resolve_release()` and the
`resolve` CLI deliberately return private pointers and are worker-only APIs.

## Local primitive

Use a private store outside the Arena checkout, its public `registry`/`web`
directories and any other static publication roots. The default check rejects
the source/package root and its ancestors or descendants. Declare additional
published roots with `--public-root` (repeatable). In-process callers pass them
through `public_roots=[...]`; an arbitrary external web root cannot be discovered
automatically.

New store directories are created with mode `0700` and records with mode `0600`.
Existing store and system directories must belong to the worker user and grant
no access to other users. Unsafe permissions and symlink records are rejected;
the module does not silently change permissions on an existing directory. Keep
private input files and backups under the same worker-only controls.

Run registration only in the private CI/worker context:

```sh
python -m arena.releases register /srv/worker/private-binding.json \
  --store /srv/worker/releases \
  --public-root /srv/arena-web
```

Standard output is the public reference. A worker can resolve a previously
registered reference with:

```sh
python -m arena.releases resolve /srv/worker/reviewed-reference.json \
  --store /srv/worker/releases \
  --public-root /srv/arena-web
```

Resolution prints the private binding: do not put its output in a public CI log,
PR, static artifact or shared result. Invalid or missing input exits with code
`2` and a generic error that does not echo private fields. Records are bounded
to 64 KiB and duplicate JSON fields are rejected.

Equivalent local calls are:

```python
from pathlib import Path
from arena.releases import register_release, resolve_release

store = Path("/srv/worker/releases")
reference = register_release(store, private_binding,
                             public_roots=[Path("/srv/arena-web")])
worker_binding = resolve_release(store, reference,
                                 public_roots=[Path("/srv/arena-web")])
```

Unit tests cover immutable and concurrent registration, idempotence, missing and
corrupt records, private permissions, public-field rejection, duplicate fields
and exact public projection. They use inert example identities and never fetch
or run a private implementation.
