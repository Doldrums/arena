# SCiEL and Shinka: prepared native pilots

`scripts/deployment/prepare_sciel_shinka.py` creates real native-run templates.
It never starts a research loop, provider request, candidate or evaluator. The
default mode can run offline; `--materialize` additionally verifies clean source
pins and creates canonical native tasks on the worker. Runtime readiness remains
unverified until the explicit native runs complete with model and receipt evidence.

The prescribed layout is `/srv/arena/{sources,envs,configs,tasks,runs}`. Sources:

| Directory | Exact source revision |
| --- | --- |
| `sources/sciel` | `0d67f813dd4ac21dee304f2b0de0b0ce59bf4157` |
| `sources/shinka` | `9912af12d423504b8d580f4179fd15f5f88b8c50` |
| `sources/autoresearch-tasks` | `5729caa7a3bd4e66c39a447c0d4ee56dc8fa0935` |

Use a distinct prepared Python environment per framework; Python 3.11 supports
both pins. SCiEL declares PyYAML, Pydantic, NumPy, Tenacity, OpenAI, greenlet and
huggingface_hub. This pilot preserves its learned grid: install CPU PyTorch and
retain the pinned `models/code_embed_v3.pt`. The SAT task has no fitted behavior
axis at this pin; SCiEL records its native fallback. Shinka declares its full
dependency list in `pyproject.toml`, including OpenAI, Anthropic, Google GenAI,
NumPy, pandas, Hydra, SciPy-related scientific packages, plotting and async I/O.
Do not combine these with historical legacy-SDK frameworks in one environment.

Root-owned read-only checkouts require a Git version that honors the launcher's
exact `-c safe.directory=/verified/source` exception. The prepared worker uses
Git **2.55.0** in `/usr/local/bin`; its official source checksum and installed
binary hash are recorded in `/srv/arena/build/git-2.55.0-release/environment.json`.
Ubuntu's Git 2.34.1 security backport rejected the command-scoped exception on
this worker. Keep `/usr/local/bin` ahead of `/usr/bin` in worker `PATH` and retain
the pinned sources' root ownership; do not replace this with a wildcard trust
exception.

Build project wheels outside the clean source checkouts. For each framework,
export the exact pin using `git --no-replace-objects archive`, extract into
`/srv/arena/build/<framework>`, then use that framework's environment to run
`python -m pip wheel --no-deps --wheel-dir /srv/arena/wheels <build-directory>`.
Install the resulting wheel with its dependencies into `envs/<framework>`;
install the built Arena wheel there too so evaluator subprocesses can import
Arena. Native launch still uses the verified source via `PYTHONPATH`. Capture
`pip freeze --all`, interpreter version and wheel hashes in worker environment
records. Upstream dependency ranges are not a lockfile: the generator does not
claim an environment is reproducible merely because its Git revision is pinned.

Use a **Linux worker-native** immutable evaluator image with NumPy/SciPy and the
task requirements. The earlier local conformance image was ARM64; its digest is
not a promise that it runs on this x86 worker. The generator requires `--image`
and never pulls, builds or substitutes an image.

After the environments and evaluator image exist, run on the worker:

```sh
/srv/arena/envs/arena/bin/python scripts/deployment/prepare_sciel_shinka.py \
  --campaign pilot-20260921 --model gpt-5.6-sol \
  --image 'YOUR_EXISTING_IMAGE@sha256:YOUR_64_HEX_DIGEST' --materialize
```

The placeholder image above must be replaced with the actual prepared digest.
Without `--materialize`, use `--output /absolute/new/template-directory` to
inspect the same configuration offline. JSON in `sciel.yaml` is valid YAML.
Materialization must write to `/srv/arena/configs/<campaign>` because launch specs
refer to that exact location. It refuses to replace existing bundles/tasks.

The bundle contains two evaluation configs, `sciel.yaml`, two native run specs,
an evidence/limits manifest, `control-templates.json` and `cpu-profiles.json`. Inspect native plans before
dispatching the corresponding `run` command:

```sh
/srv/arena/envs/arena/bin/python -m arena.frameworks plan /srv/arena/configs/pilot-20260921/sciel.run.json
/srv/arena/envs/arena/bin/python -m arena.frameworks plan /srv/arena/configs/pilot-20260921/shinka.run.json
```

`manifest.json` records the exact explicit `run` argv. Execute through the
worker's admitted, bounded launch path after gateway and environment checks;
the generator does not submit to the queue.

To bind an already captured operator probe, pass
`--probe-evidence /srv/arena/configs/model-probes-20260921.json`. The generator
requires a successful generation record for the exact requested/response model,
consistent token usage and duration. It copies that nonsensitive record into
`provider-probe.json` and hashes its source. Only materialized bundles with this
proof emit ready control templates; offline bundles remain blocked. This ready
state permits admission after the operator verifies the worker/proxy services;
it does not claim a completed native research run. The two templates allocate
`{output_dir}` through the control service and leave trusted cgroup/receipt
environment values to its worker. Research execution stays false in the bundle.

## Native behavior and provider boundary

SCiEL receives 12 native evaluations, at most 24 ordinary search iterations,
three islands and one concurrent worker. Native portfolio seeding, crossover,
ideas, learned grid and research memory remain enabled; research auxiliary
calls are limited to four. Research-tool episodes remain at their native
disabled default; this is not conformance for that optional subsystem. The
reviewed canonical bridge currently permits only `reference-sat`: its seed
already scores **1.0 on ten fixed development instances**. A successful pilot
therefore establishes a real generation/evaluation/archive cycle, not improved
SAT performance or a held-out result.

Shinka receives six generations, one evaluator/proposal/database worker, one
numeric thread per evaluation, two islands and no embedding API. Its task is
`alphaevolve-circle-packing-in-unit-square`. Both use Docker canonical receipts;
SCiEL and Shinka scores concern different objectives and must not be compared
as a scientific ranking. Seed-only output is insufficient: retain at least one
real model-generated candidate, lineage and canonical receipt.

The gateway is `http://127.0.0.1:8789/v1`. Only its per-worker key is supplied in
`OPENAI_API_KEY`; no key is written into templates. SCiEL uses `llm.api_base` and
`api_key_env`. Shinka uses its native dynamic local model syntax:
`local/gpt-5.6-sol@http://127.0.0.1:8789/v1?api_key_env=OPENAI_API_KEY`.
This query contains an environment **name**, which native Shinka removes before
calling the endpoint. Other credential queries remain rejected by the adapter.

This configuration needs the gateway's explicit `codex-native` compatibility
policy. Its `max_tokens` and sampling arguments are **not enforced upstream**;
the manifest records that limitation. They are not a provider compute cap.
Shinka's local backend returns zero estimated price for uncataloged model IDs;
SCiEL may use generic token estimates. Neither value proves zero real spend.
Use external request/admission limits, wall timeout and gateway/provider usage
receipts. Native retry/resampling behavior remains native; the generator does
not silently modify its optimizer. Probe the exact chosen alias first: model
discovery alone does not establish successful generation.

Generated Docker configs require admitted control execution. The worker supplies
`ARENA_EVALUATION_CGROUP_PARENT`, `ARENA_EVALUATION_RECEIPTS_DIR` and `DOCKER_HOST`.
The evaluator checks that its actual cgroup membership belongs to that run,
requires Docker cgroupfs/v2, and labels/parents the container under the same
admission envelope. Receipts go to that run's
`artifacts/canonical-evaluations/<evaluation-directory-id>`, overriding the
static standalone receipt path. Missing or mismatched admission fails before
container launch. The worker receives only the restricted evaluator Docker
proxy socket, never membership in the real Docker socket group. Proxy access
is retained for cleanup. A plain native `run` outside the admitted worker is
therefore intentionally insufficient for these controlled templates.

Set the manifest's nonsecret `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, and `NUMEXPR_NUM_THREADS` values to `1` in the admitted worker
environment. Every pilot asks for an initial envelope of four CPUs, 8 GiB, one
evaluation slot and 512 processes. These are planning limits, not measured
peaks. Canonical Docker evaluations separately cap one CPU and 2 GiB; they
do not automatically inherit host BLAS environment variables. No GPU is needed
for these two selected CPU tasks or API-backed generators.

## CPU-first expansion inventory

Every source-verified recipe profile appears in the generated inventory with its
source pin, evidence hashes, native evaluator contract, setup and limitations.
`cpu_packaged_task` identifies mathematical/local-data candidates such as
AdaEvolve/EvoX, BASE, CodeEvolve, EoH, ReEvo/HSEvo/MCTS-AHD, MEoH, CoEvo,
LoongFlow and Darwinian Evolver. This is deployment triage, not a claim that all
their provider endpoints are compatible or dependencies installed.

`cpu_requires_inputs` separates factory/data-dependent profiles such as
OpenEvolve, original FunSearch, GEPA, MIPROv2, symbolic-regression libraries and
dataset-based agent/prompt searches. Provision reviewed inputs first. Profiles
requiring simulators, GPUs, specialized hardware or additional CLI/cgroup services
are kept separate; unreviewed cases are explicit. In particular EvolCAF fixes
**20 inner joblib workers** despite its outer `--processes` setting: do not admit
it as a one-CPU evaluator. LaSR needs Julia, retrieval profiles need Java/data,
and CodeEvolve requires Python **3.13.5 or later** at its pin. These definitions
cannot share one generic resource allocation or universal environment.
