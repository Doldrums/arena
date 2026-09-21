# CodeEvolve, LoongFlow and CoEvo CPU pilot preparation

These profiles preserve each pinned implementation's complete native optimizer
and native evaluator. Preparation does not run optimization, evaluate candidates
or call a model. The queue operator must explicitly admit the prepared templates.
They are not a common canonical benchmark and runtime readiness remains
`not_verified` until actual pilots return evidence.

| Engine | Source commit | Python | Native task / pilot budget |
| --- | --- | --- | --- |
| CodeEvolve | `c077959e1ab24b060aaa6d4c563bca2e9cbe8617` | 3.13.5 | Pack 26 circles in a square; 1 island, 4 epochs, initial population target 2, 60-second native evaluation timeout |
| LoongFlow | `945c78bc1554f8281aac40320b3599bd68d528d7` | 3.12.12 | Pack circles in a square; 4 PES iterations, 1 executor round, planner/executor/summary ReAct steps 3/3/2, 60-second native evaluation timeout |
| CoEvo | `dcad65e9799961cf67cf29865ff41dda2902a808` | 3.11.16 | Oscillation-1 symbolic equation discovery; population 2, initialization plus 1 complete offspring round, summarizer retained |

All 21 templates use the exact seven configured aliases, 4 CPU, 8192 MiB RAM,
512 PIDs, one admitted native evaluation slot and a 2400-second whole-process
timeout. Numerical thread environment variables are set to one. These controls
contain resources; they do not sandbox generated code.

CodeEvolve evaluates serially within its single native island. LoongFlow has
`evolve.concurrency=1`, executor `max_rounds=1` (its candidate slots otherwise
increase with each round), and its original planner/executor/summary each use
`SequenceActor`. CoEvo evaluates synchronously. These bounds are supported by
the hashed source files in `program-search.json`.

CoEvo's pinned implementation leaves its generation counter at zero after
initialization, despite its docstring saying initialization is included in
`max_generations`. Therefore native `--max_gen 1` yields four initialization
chains and ten new/crossover/mutation chains: up to two generated solutions per
chain, before retries. Failed or non-improving continuation solutions need not
be registered in history. The task's `timeout_seconds=30` field is **not enforced**
by its direct `exec`/SciPy evaluator. Only the external 2400-second process/cgroup
timeout stops a hung candidate. No substitute evaluator is introduced.

## Provider seams and credentials

The worker supplies only `OPENAI_API_KEY`, containing the scoped local gateway
credential. Configuration files and receipts contain no key values.

* CodeEvolve's wrapper maps the credential into its native `API_KEY` environment
  name and sets `API_BASE=http://127.0.0.1:8789/v1`. Native YAML selects the exact
  model for both ensembles and the auxiliary sampler. Its unchanged
  `OpenAILM.generate` emits a `user_<uuid>` tracking field unsupported by the
  current gateway. A narrow HTTP transport extension validates `user` as a
  string of at most 256 characters and removes only that field. A native receipt
  records `discarded_metadata:["user"]`, never its value. All messages, exact
  model aliases and generation controls are preserved. Linux's native `fork`
  backend is required so island workers inherit this client binding.
* LoongFlow's native LiteLLM configuration uses the HTTP gateway, the exact model
  alias and `model_provider:openai`. Its optional API key is omitted so LiteLLM
  reads the environment. Optional `temperature` and `top_p` are omitted explicitly:
  the gateway cannot enforce them and LiteLLM rejects them for GPT-5 aliases.
  Its native Plan–Execute–Summary loop and sequence actors are unchanged.
* CoEvo's `evotoolkit==1.0.2` client always uses `HTTPSConnection`, even for an
  `http://` URL. Its native client therefore uses the verified loopback TLS relay
  at `https://127.0.0.1:8790/v1/chat/completions`, with the public combined system
  and local CA bundle supplied as a hashed request input. No TLS checks are
  disabled. The isolated source's credential placeholder `model_config.json`
  is removed under the existing declared recipe rule, enabling its native env
  fallback. The driver refuses a remaining file or symlink at that path.

The gateway's `codex-native` policy records unsupported sampling/token-limit
controls as unenforced. Native sampling configuration is not a promise that the
upstream provider implements those controls. No existing provider/worker service
is restarted by this preparation.

## Environments and offline embedding cache

Source checkouts are root-owned and remain clean under `/srv/arena/sources`.
Separate build copies are under `/srv/arena/build/<engine>-pilot-source`.
`uv` installed exact interpreters 3.13.5 and 3.12.12 under `/opt/arena/python`;
CoEvo uses the existing 3.11.16 interpreter. Native environments are root-owned
under `/srv/arena/envs/<engine>` and dependency freezes are recorded at
`/srv/arena/configs/pilot-dependencies-<engine>.txt`. Each RunSpec hashes a copy
of its freeze as an input. The full CodeEvolve optional benchmark dependency
set is not installed; the packaged CPU circle task has NumPy and SciPy.

CoEvo uses `torch==2.8.0+cpu`, `transformers==4.57.6` and `evotoolkit==1.0.2`.
Its native summarizer requires model weights as well as a tokenizer. The
[official GPT-2 repository](https://huggingface.co/openai-community/gpt2/tree/607a30d783dfa663caf39e06633721c8d4cfcd7e)
is pinned to `607a30d783dfa663caf39e06633721c8d4cfcd7e` and cached under
`/srv/arena/caches/coevo-hf`. The cache's manifest names and hashes all eight
downloaded files. Before native imports, the driver verifies the exact revision,
the offline `main` reference and every file hash; resolved cache links must stay
inside the cache. `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` prevent downloads
during a run. Loading the tokenizer/model was checked without a forward pass.

LoongFlow's optional generated-code package-install tool may fail against the
read-only shared environment. This is recorded rather than allowing changes to
the common native environment. Generated code that needs unprepared packages
can fail native evaluation.

## Prepared artifacts and verification

`scripts/deployment/prepare_additional_program_pilots.py --engine ENGINE` creates
the seven templates, pure native plans, native YAML and preparation receipt under
`/srv/arena/configs/program-pilots-20260921-ENGINE`. Run the preparation script
with an interpreter containing PyYAML, such as the prepared CodeEvolve Python.
It validates the exact clean source pin and the control admission schema but
does not enqueue anything.

`scripts/deployment/check_additional_program_pilots.py --engine ENGINE` runs with
the engine's prepared interpreter. It parses the native configuration and calls
only each real native provider client against temporary fixed-response HTTP/TLS
fixtures. A Python network audit rejects all external endpoints, including the
real gateway. It checks all seven exact model aliases against the gateway's
request normalizer. Optimizers and task evaluators are not instantiated or run.
The fixtures were also checked as the actual unprivileged `arena` worker user.

Source pins, environment freezes, prepared plans and successful transport
receipts are setup evidence. They do not establish model availability, candidate
quality, research validity or successful end-to-end execution.
