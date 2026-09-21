# SCiEL private-image deployment

A public release record remains exactly `schema`, `system` and `version`. A
version update does not replace the public SCiEL adapter's audited source pin.
Private versions use the separate `sciel-release` execution backend, which
resolves an approved private manifest before the shared runtime checks the source
commit. Its host Python process is a broker client. SCiEL itself executes in the
approved image; there is no host-venv fallback.

The operator preparation tool is `python -m arena.release_deployment`. It never
builds, pulls, pushes, runs or publishes an image. Preparation, approval, template
installation and an authenticated queue submission are separate operations.
The root-owned broker independently verifies approval and image identity at each
execution; a local manifest or a public PR alone cannot authorize a container.

## Release and image preparation

1. An external contributor edits SCiEL in its private repository and opens the
   private source PR. Private CI reviews/tests the exact commit and builds its
   worker image, including the SCiEL package, Arena evaluator bridges, modern Git
   and Docker client needed by its reviewed task profile.
2. CI or the private operator records a real immutable image repository digest.
   A local Docker `Id` is an image configuration digest and cannot be substituted
   for a repository manifest digest. The image must be addressable as
   `repository@sha256:…` and its actual `RepoDigests` must contain that reference.
3. Register the system/version binding with `arena.releases register` in a private
   store. It binds that exact commit and image once. Public output contains only
   the release reference. The Arena PR contains that reference, never private
   repository URLs, commits, image pointers or credentials.
4. Review the Arena PR and the corresponding private CI/operator evidence. The
   example version `1.0.4` is not a registered release. An operator-local version
   such as a real package version plus commit build metadata must be clearly
   identified as local; it is not evidence that an upstream tag was published.

The `sciel-cli-v1` image contract declares this entrypoint:

```json
["/opt/venv/bin/python", "-m", "sciel.cli.main"]
```

It also declares these labels, exactly matching the private binding:

| Label | Value |
| --- | --- |
| `org.opencontainers.image.revision` | Full bound Git commit |
| `org.opencontainers.image.source` | Credential-free bound repository URL |
| `io.arena.sciel.contract` | `sciel-cli-v1` |

Labels are reviewed metadata, not a cryptographic build attestation. CI must
establish that the image was built from the reviewed source. The broker compares
the actual daemon image ID, repository digest and contract labels again. The
image runs as the configured unprivileged worker UID/GID. No host SCiEL checkout
or host Python dependency environment is mounted over image code.

## Private operator manifest

Save the image's actual `docker image inspect` JSON in a private file. Prepare a
manifest using the reviewed public reference, registered binding and clean local
checkout of the same commit:

```sh
python -m arena.release_deployment prepare \
  --reference /srv/operator/reviewed-reference.json \
  --store /srv/operator/releases \
  --source /srv/arena/sources/sciel-release-checkout \
  --image-inspection /srv/operator/image-inspection.json \
  --broker-socket /run/arena-engine/sciel-images.sock \
  --operator release-reviewer \
  --review-reference arena-pr-reviewed-reference \
  --output /srv/operator/deployment.json
```

The output directory must be owned by the caller and mode `0700`; the new file is
created with `0600` using create-only semantics. The source inspection runs Git
read-only and never imports private SCiEL code. Existing source changes or a
different commit fail closed. Standard output includes the public release,
manifest hash, and `prepared_not_admitted`, without private pointers.

The private manifest contains the binding and its hash, verified source commit
and tree, selected image metadata, broker socket, native contract and operator
review reference. It omits Docker `Config.Env`, arbitrary labels and build
history. The `check` command validates this bounded artifact without running it.

After review, the broker administrator installs a byte-identical copy named
`<raw-file-sha256>.json` in the broker's root-owned `0700` approval directory;
approval files are root-owned `0600`. The worker receives a separate readable
copy, preferably root-owned `0640` in a root-owned `0750` directory whose group is
the worker group. Keep the source preparation store, approval store and readable
manifest copies outside Git and public static roots. Do not use a hard link
between operator approval and a worker-writable copy.

The approval directory is a local authority, not a portable signature scheme.
The broker must never use a caller-provided manifest as its approval authority.
It looks up the exact hash in its own configured root-owned directory.

## Materialize one reviewed native template

The operator creates a private control template only after the worker manifest
and hash-named broker approval match byte for byte:

```sh
python -m arena.release_deployment template \
  --manifest /srv/arena/release-manifests/sciel-reviewed.json \
  --approved-manifest /srv/arena/releases/approved/ACTUAL_MANIFEST_SHA256.json \
  --python /opt/arena/venv/bin/python \
  --config /srv/arena/configs/sciel-reviewed.json \
  --tasks-root /srv/arena/prepared/sciel-reviewed-tasks \
  --id sciel-reviewed-model-profile \
  --name 'SCiEL reviewed private image' \
  --model REVIEWED_GATEWAY_MODEL \
  --cpus 4 --memory-mb 8192 --evaluation-slots 1 --pids 512 \
  --timeout-seconds 3600 --budget 4 --seed 0 \
  --verified-native-concurrency \
  --output /srv/operator/sciel-template.json
```

The paths, model and numbers above illustrate the interface and are not a ready
deployment. The operator must prepare the actual native config and task profile,
verify its maximum nested evaluation concurrency, review the model and wall-time
budget, and choose resources that fit the real worker pool. The explicit flag
records that native concurrency review; it does not automatically prove it.

The resulting template has framework `sciel-release`, contains the public
release and private deployment path in its native request, and uses
`output_dir: "{output_dir}"`. It records `status: "ready"` as an operator-approved
template; this does not assert that an experiment has run or passed evaluation.
The command prints `template_prepared_not_submitted` and does not change the
control configuration, submit work or spend model budget. The operator installs
the template in the private configuration and reloads the service. Actual global
capacity and key budgets are checked by the control queue at admission.

An authorized external agent then submits only the template/model identity to
`POST /api/queue`, with its explicit run key and optional idempotency/batch IDs.
It reads its own run status and, with `logs:native`, redacted native diagnostics.
It never sends an image name, repository pointer, container command, mount list
or credential value to the broker.

## Execution and receipt boundary

The adapter fixes the host argv to the Arena broker-client module and includes
the manifest, config and tasks in input provenance. The client requires trusted
control-run environment metadata and connects to the root-owned Unix service;
Linux `SO_PEERCRED` verifies that the peer is root.

The client sends only `run_id` and `deployment_sha256` to `POST /v1/run`. The
broker authenticates the calling process's run cgroup, independently loads the
admitted snapshot and approved manifest, derives fixed CLI paths and mounts,
and starts the actual image under the admitted resource cgroup. The initial
private-engine profile uses host networking for its reviewed local gateway and
broker context; this is trusted-framework execution, not hostile-code network
isolation. Only a scoped gateway key is available to the engine; the upstream
provider JWT stays outside native environments.

The broker streams bounded NDJSON start/log/result frames. A successful final
frame must include the admitted run ID, exact manifest hash, actual image
reference and image ID, bound source commit, `status: "completed"` and exit code
zero. Missing, malformed or mismatched final provenance makes the driver fail;
it cannot fall back to host execution. Cancellation closes the stream and sends
an explicit owned-run DELETE request; the control cgroup independently contains
the engine and its descendants.

The output's `.arena/private-image-result.json` is a private worker-local receipt
copy. Authoritative broker records remain in the root-private broker store.
Native results are still marked `canonical_evaluation: false`; individual Arena
evaluator receipts establish candidate fitness/validity separately. Reading a
receipt copy is not itself cryptographic proof of image execution.

The validator, adapter and client have inert source/transport tests. Live private
image execution and deployment readiness require the separately implemented
broker and an actual approved image; the preparation commands alone do not
establish those conditions.
