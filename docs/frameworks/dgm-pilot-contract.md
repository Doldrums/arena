# DGM two-exercise pilot preparation

This is prepared source/data/provider integration, **not a runnable or evaluated
DGM claim**. No model request, coding exercise, container or optimizer was run
during preparation. A separate restricted DGM broker, approved immutable images
and an explicitly launched fresh baseline are prerequisites.

The source is `jennyzzt/dgm` at
`a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2`. The public benchmark is
`Aider-AI/polyglot-benchmark` at
`7e0611e77b54e2dea774cdc0aa00cf9f7ed6144f`, restricted to the native
`python__dominoes` and `python__beer-song` exercises. Upstream DGM imports
SWE-bench even for Polyglot; its README-pinned import dependency is
`SWE-bench/SWE-bench@dc4c087c2b9e4cefebf2e3d201d27e362d899e0f`.
No SWE-bench dataset or external credentials are needed for these exercises.

## Prepared files and provenance

On the preparation machine the clean checkouts are `/srv/arena/sources/dgm`,
`/srv/arena/dependencies/polyglot-benchmark` and
`/srv/arena/dependencies/swe-bench-dgm`. The isolated host environment is
`/srv/arena/envs/dgm` (Python 3.11); its freeze is
`/srv/arena/configs/pilot-dependencies-dgm.txt`. This host environment does not
prove the native Docker images are installed or usable.

`scripts/deployment/prepare_dgm_pilots.py` requires those exact clean source
pins and a new destination. It copies only the two original exercise trees,
then calls upstream `register_git` and `generate_dataset_metadata`. Synthetic
Git author/date settings make the exercise base/test commits reproducible.
It never invokes a native harness or model. The resulting directory contains:

- `preparation.json`: original benchmark file hashes, native input hashes,
  native exercise commits, source/overlay hashes and dependency freeze hash.
- `native-inputs/polyglot`: native benchmark metadata and exercise Git trees.
- `provider-overlays`: three explicitly changed native source files.
- `native-image-recipes.json`: pure upstream TestSpec Dockerfiles/scripts and
  image lookup names. This file does not build, pull or approve an image.
- `plans.json`: seven `prepared_not_runnable` model plans, one for each exact
  gateway model. These are not control-queue templates.

## Provider seam

`src/arena/frameworks/drivers/dgm_gateway.py` checks SHA-256 of every changed
native file before producing an overlay. Unmodified source remains pinned.
The narrow changes are:

- Route `llm.create_client` to the scoped gateway and select the native OpenAI
  code paths by an explicit supported model, preserving that exact wire ID.
- Set diagnosis, coding and self-improvement model constants to that same
  selected ID. Unknown or mismatched models fail before native retries.
- Fix native OpenAI terminal-output detection: a final message with no
  function call must terminate the loop rather than being treated as a call.
- Use `image_name = "dgm:latest"` for the native exact tag-membership check.
  This is a lookup alias only; the broker must bind it to an approved immutable
  ImageID and RepoDigest and must not perform runtime builds or pulls.

Native prompt construction, diagnosis parsing, OpenAI Responses tool schema,
function-call IDs, tool dispatch, retries, search, patches and evaluator remain
upstream. The integration does not rename the selected model to a legacy
`o1`, `o3`, GPT-4 or Claude identifier. `ARENA_DGM_MODEL` chooses an exact model;
`OPENAI_API_KEY` contains only a scoped local gateway key. The worker uses
loopback `http://127.0.0.1:8789/v1`. The root broker supplies the container's
fixed internal-bridge `ARENA_DGM_GATEWAY_URL` (planned
`http://172.30.88.1:8789/v1`). The provider helper rejects credential-bearing,
non-private, non-HTTP or non-`/v1` endpoint forms; the broker independently
pins the exact endpoint and bridge network identity. No upstream JWT enters
the worker, database, source overlay or image.

`scripts/deployment/check_dgm_gateway.py` loads the overlaid native modules
inside a temporary source copy. The real OpenAI SDK talks only to an inert
local HTTP fixture; an audit hook denies every other socket destination.
It verifies 35 requests across seven exact models, 14 native tool round trips,
all three model roles, wrong-model rejection and three native CLI help paths.
Only the fixture tool executes; it returns text and has no filesystem or shell
action. The gateway's `codex-native` policy records native diagnosis
`temperature` and `seed` as unenforced controls. Neither those parameters nor
native generation count establish a paid-token ceiling.

## Required scoped Docker operations

All source anchors below refer to the DGM commit above. This is the contract
for the separate broker, not permission to expose the Docker daemon.

| Native operation | Source anchor | Restricted behavior needed |
| --- | --- | --- |
| Find DGM image and create/start idle container | `utils/docker_utils.py:104–138` | Filter image listing to approved lookup aliases; use immutable image identity. `dgm:latest` must exist. Deny build/pull. |
| Check base/env/instance image freshness | `polyglot/docker_build.py:197`, `:252`, `:468` | Return real approved image `Created` and identities; prebuild in parent-first order. Do not forge cache hits or timestamps. |
| Create Polyglot container | `polyglot/docker_build.py:523–541` | Only the two approved instance images and validated native name prefixes; native `root`, `tail -f /dev/null`, `linux/x86_64`. Broker supplies cgroup/resource/security/network policy. |
| Upload code, parent patch and evaluation script | `utils/docker_utils.py:149–185`; `swe_bench/utils.py:104–140` | Bounded tar input restricted to `/dgm` or `/testbed`, regular files/directories only. Reject traversal, links, devices and oversized members. |
| Execute native setup, coding and tests | `self_improve_step.py:276–358`; `polyglot/harness.py:67–182` | Own containers only. Native working directories are `/`, `/dgm`, `/testbed`; retain actual command/exit status. No arbitrary mounts, privilege flags or host namespaces. |
| Read chat and patch artifacts | `utils/docker_utils.py:196–253`; `swe_bench/utils.py:151–208` | Restrict artifact paths; validate and bound outbound archives before forwarding. Native helpers call `tar.extractall`, so source-side trust alone is insufficient. |
| Cleanup | `utils/docker_utils.py:140–146`; `polyglot/docker_build.py` | Stop/delete only containers owned by the admitted run. Cancellation and lease reconciliation must remove every owned container and bound exec lifetime. |

Self-improvement works in writable `/dgm`, including its `.git`, applies parent
patches, commits changes and invokes
`timeout 1800 python /dgm/coding_agent.py ... --self_improve` with workdir `/`.
Polyglot copies `coding_agent_polyglot.py` as `/dgm/coding_agent.py`, framework
helpers and both provider files, then runs
`timeout 600 python /dgm/coding_agent.py ... --git_dir /testbed/` with workdir
`/testbed`. It restores the native test commit, stashes/restores only solution
files and invokes `timeout 120 ./eval.sh`. Native Python evaluation executes
`pytest -rA --tb=long` (`polyglot/harness.py:28,174–188`). The executed script
does **not** activate conda; do not substitute the unused TestSpec evaluation
script and claim the same interpreter behavior.

Native DGM uses Python 3.10 under `/usr/local` in its Dockerfile. Polyglot's
base image has `/opt/miniconda3/bin` in PATH and separately creates the native
`testbed` Python 3.11 environment (`polyglot/dockerfiles.py:59–80`,
`polyglot/constants.py:62–81`). Preinstall DGM dependencies and pytest in the
actual plain-`python`/`pytest` interpreter used at runtime. Preserve native PATH
and include the Arena provider helper in the image; do not depend on a host
source overlay or the host venv.

A viable bounded writable layout is a read-only image root with separate
size-bounded tmpfs mounts for `/dgm`, `/testbed`, `/tmp` and necessary writable
home/cache state. An image bootstrap copies immutable directory templates,
including exercise/framework `.git`, into those mounts before native idle
startup. Native image dependencies and lookup identities must be prepared and
recorded first. This design still needs an actual image/broker conformance
check. Runtime Internet/PyPI access stays disabled; native runtime `pip install`
must find every requirement already satisfied. An evolved dependency that is
not preinstalled is an honest run constraint, not a reason to enable networking.

The broker must inject the selected model and fixed gateway endpoint at
container creation: native `exec_run(environment=...)` forwards its historical
API-key variables but not the new Arena variables. The broker substitutes its
scoped gateway credential and never accepts raw worker-supplied secrets. Native
exec/log/archive responses require bounded output and secret redaction before
exposure; only the admitted run may inspect or remove its containers. Resource
limits must include all container descendants in the run's cgroup; host process
limits alone do not constrain daemon-created containers.

## Fresh baseline and native search plan

The repository's `initial_polyglot` is a cached 225-task run. Shrinking
`polyglot/subsets/small.json` alone leaves diagnosis sampling from that old
archive (`DGM_outer.py:15–35,50–147`; `prompts/self_improvement_prompt.py:343`).
Each exact selected model therefore needs its own fresh two-task initial
archive and native logs. This step **does make model calls** and must be
explicitly launched after image/broker approval; it was not executed here.

The prepared baseline plan calls native `polyglot.harness.harness` with the
two IDs, `model_patch_paths=[]`, `max_workers=1`, `num_evals=1`,
`num_evals_parallel=1`, explicit run/model label and fresh output directories.
Collect native `utils.evo_utils.get_all_performance` and record its submitted,
resolved, unresolved and empty-patch IDs. Require exactly the two intended task
IDs and retain native chat, patch and test logs. A failed or incomplete baseline
must not become a valid initial score. If both exercises are solved, native
failure-driven diagnosis has no unresolved task; report that scope limitation
rather than inventing a failure or changing task selection silently.

Place this fresh archive at the isolated workspace's `initial_polyglot` and
replace its `small.json` with the hash-recorded two-ID subset. Then use native
`DGM_outer.py --max_generation 1 --selfimprove_size 1 --selfimprove_workers 1
--num_swe_evals 1 --shallow_eval --no_full_eval --polyglot`. The native search
and benchmark remain intact. `self_improve_step.py:180–198` chooses up to two
parallel exercise evaluations for this subset even with one outer worker;
reserve **two evaluation slots**, not one. A conservative initial admission is
4 CPUs, 16 GiB, 1024 PIDs and an outer 3600-second timeout, subject to actual
image conformance. Results are native DGM/Polyglot results, not Arena's canonical
task-library evaluation. No runtime readiness is asserted by these preparation
files or inert fixtures.

## Recorded preparation check

On 2026-09-21 the worker UID `arena` completed the fixture above in the separate
DGM environment: 35 fixture requests, 14 tool round trips and three native CLI
help/import checks passed for all seven models. The focused local DGM suites
passed 55 tests. All three upstream checkouts remained clean. Repeating native
exercise preparation produced identical base/test commits.

The VM preparation manifest SHA-256 is
`105792ef072ad4ae0e311c0d41d3cbcb46317731f5b08b5dbc729595db6c4808`;
the dependency freeze SHA-256 is
`20ed2d7f11d70e4cf18d97ebafa3c547b900bb33afa64da85232cfd8c45a0143`.
The manifest covers 14 original exercise files and 88 prepared files, including
native Git metadata. Both exercises derive the native environment lookup key
`pb.env.x86_64.ce9e95520b42abb86d1825:latest`. The fixture result is
`/srv/arena/configs/dgm-pilot-20260921/worker-provider-fixture.json`.
These checks still record zero model calls, task evaluations, container runs
and optimizer runs; they do not establish image or research readiness.

## Explicit operator image build

`scripts/deployment/prepare_dgm_images.py` generates five private contexts from
the verified preparation: DGM, the original all-language Polyglot base, its
Python environment, and the two exercise images. It resolves the original
Docker Hub base tags to verified Linux/amd64 manifest digests and records those
pins. Contexts contain public pinned source, native exercise Git trees, the
reviewed provider overlay and a minimal Arena provider package. They do not
contain worker configuration or credentials. The script scans context files
for private-key/token material, credential-bearing Git configuration, `.env`
files and unexpected symlinks, then hashes every context file.

After operator approval, `scripts/deployment/build_dgm_images.py` builds one
named context. Build parent-first: `polyglot-base`, `polyglot-env`, then the two
`python__*` images; DGM is independent. Child builds require
`--parent-receipt` and verify the parent's actual ImageID and repository digest
before and after the build. The native lookup aliases remain available to
DGM, while the restricted runtime broker binds approved aliases to immutable
images separately.

The build driver uses a separate empty Docker client configuration, the classic
builder's CPU/memory flags and a dedicated cgroup v2 parent. Each Dockerfile
first asserts actual `cpu.max=800000 100000` and
`memory.max=25769803776`; a builder that ignores those limits fails before
package installation. These limits cover build `RUN` processes, not all daemon
work such as downloading and unpacking image layers. No global daemon setting
or running research service is changed. The driver requires 80 GiB free before
each build and publishes only to the operator's existing loopback registry.

The native dependency ranges resolve at build time. Receipts preserve actual
interpreter freezes, package installation reports with download hashes where
available, conda explicit packages, system package versions, native setup-file
hashes, build logs, context hash, ImageID and RepoDigest. This is recorded build
provenance, **not a preexisting fully locked dependency graph**. In particular,
the host Python 3.11 freeze must not be imposed on native DGM's Python 3.10.

Runnable images keep their native `/dgm` and `/testbed` trees as immutable
`/opt/arena-dgm-template` and `/opt/arena-testbed-template` seeds. The fixed
bootstrap copies them using `cp -a --no-preserve=ownership`, restores reviewed
home configuration, then creates `/tmp/.arena-dgm-ready` and starts the native
idle command. Rust home trees remain immutable with fixed home symlinks, so
the original all-language installation is retained without copying toolchains
into a small writable home mount. Broker metadata requires the exact bootstrap
entrypoint, native idle command, source revision label and
`io.arena.dgm.contract=dgm-prebuilt-v1`; no image volume or healthcheck is used.

Offline conformance uses four CPUs, 8 GiB, 512 PIDs, a read-only root,
`--cap-drop ALL`, `no-new-privileges`, bounded tmpfs mounts and `--network none`.
For Polyglot it reproduces the native framework file uploads before checking
imports and CLI help. It checks bootstrap readiness, Python/pytest and pip
consistency, and that native runtime `pip install` succeeds with `PIP_NO_INDEX=1`
because requirements are already installed. It does not execute an optimizer,
coding exercise, evaluator or model request. The resulting build receipt still
has `broker_approved: false`; image publication is not run admission.
