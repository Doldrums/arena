# EoH and MEoH CPU pilot preparation

The private worker has 14 prepared templates: one native online-bin-packing
profile for each of EoH and MEoH across `gpt-5.6-sol`, `gpt-5.6-terra`,
`gpt-5.6-luna`, `gpt-6-astra`, `gpt-5.5`, `gpt-reserve`, and
`codex-auto-review`. Preparation does not submit or run them. Native optimization,
evaluation, and model inference readiness remain `not_verified` until explicit
queue execution produces evidence. These are small integration pilots, not
paper reproductions or comparable cross-framework benchmark scores.

| Engine | Exact source | Native task and budget |
|---|---|---|
| EoH | [FeiLiu36/EoH](https://github.com/FeiLiu36/EoH/tree/472545785c936dcfc863d2bc0d6109cf23c7ce62) | Packaged `examples/bp_online` evaluator; population2, generations2, four evolution samples. Native initialization adds four samples, for eight candidate records. |
| MEoH | [Optima-CityU/LLM4AD](https://github.com/Optima-CityU/LLM4AD/tree/ffb6acf64497be93932c98d25369352efd3865cf) | Packaged two-objective online bin packing; population4, generations2, at most eight registered samples including initialization. |

Each template reserves 4 CPUs, 8192MiB RAM, one evaluation slot and 512 PIDs for
the whole admitted run, with a 2400-second wall limit. Both drivers explicitly
set one sampler, one evaluator and one numeric-library thread. Individual
evaluations have a 60-second native timeout. The native evaluator pools are the
source of the one-slot admission guarantee; generated Python still executes as
trusted worker code under cgroup resource/lifecycle containment, not a security
sandbox.

EoH's `max_sample_nums` excludes its `2*population` initialization. Its native
constructor also makes a connectivity probe. MEoH can finish at its generation
boundary before registering eight samples. Retries, parsing failures and native
provider backoff can increase API request counts; sample settings and the
provider's nominal output-token settings are not a monetary or token ceiling.
MEoH's native HTTPS client retries indefinitely; the outer worker wall limit
remains authoritative.

## HTTPS transport and credentials

Both pinned providers call `http.client.HTTPSConnection(host)` and POST
`/v1/chat/completions`. The deployment uses `arena-local-tls.service`, listening
only on `127.0.0.1:8790`, with the fixed upstream `127.0.0.1:8789`. It runs as the
separate `arena-relay` user. The relay preserves native request bodies, forwards
Authorization only to that fixed local gateway, and never opens a credential
file or logs request bodies/Authorization. Upstream authentication still applies.
It allows only the chat-completions POST and models GET, with bounded request,
response, header, concurrency and total-duration limits. It supports the
nonstreaming clients used here; it does not expose arbitrary proxy routes.

`setup-local-tls.py` creates a root-only CA private key and a distinct relay leaf
key readable by the relay group. The worker gets only the public combined trust
bundle `/etc/ssl/certs/arena-worker-bundle.pem`, which preserves system CA trust.
Each template supplies that bundle as a hashed `request.inputs` file. The
driver's explicit `--tls-ca` validates it and sets `SSL_CERT_FILE` before native
provider construction. Certificate and hostname verification stay enabled. The
active worker service needs no restart. Initial leaf expiry is 2026-12-20 UTC;
an operator must renew the certificate and reload the relay before expiration.

Only the local gateway key is inherited through `OPENAI_API_KEY`. No upstream
provider JWT enters these environments. The pinned MEoH profiler prints the
provider's `__dict__`, including the native `_key` field. The Arena driver uses a
subclass whose `_key` property reads the environment at request time, leaving
no key in that dictionary. Its inherited native `draw_sample` implementation is
unchanged. Search, operators, objectives and evaluators are not replaced.

The gateway's explicit `codex-native` compatibility policy records unenforced
generation controls. MEoH sends `max_tokens=8192` and `temperature=1`; these must
not be represented as enforced compute or sampling guarantees. EoH omits them.

## Prepared files and dependency evidence

Sources remain clean at `/srv/arena/sources/{eoh,meoh}`. The separate Python3.11
environments are `/srv/arena/envs/{eoh,meoh}`; native code is imported from the
verified workspace copy, without an editable installation or mutable Git
dependency. Full installed-package freezes are recorded in
`/srv/arena/configs/pilot-dependencies-{eoh,meoh}.txt`; repository copies live in
`scripts/deployment/requirements-{eoh,meoh}-pilot.txt`.

MEoH's broad setup includes unused GPU/UI dependencies and a moving LLaMEA
`main` dependency. The selected native profile instead has its necessary CPU
dependencies installed explicitly. A real native `calc_syntax_match` check
exposed an upstream dependency conflict: `tree-sitter-python==0.23.0` returns a
capsule that CodeBLEU0.7.0's supported tree-sitter0.22.3 cannot consume. The
prepared environment uses tree-sitter-python0.21.0, with the same native
CodeBLEU and MEoH logic. This compatibility choice is recorded, not concealed
as an exact reproduction of all upstream requirements. The selected dependency
environment passes `pip check` and the native AST-similarity helper fixture.

`prepare_heuristic_pilots.py --engine eoh` and `--engine meoh` create pure plans,
`templates.json`, and `preparation.json` under
`/srv/arena/configs/heuristic-pilots-20260921-{eoh,meoh}`. The generator validates
the source pin, CA input, planner and control schema. It neither modifies the
live control configuration nor queues work. Each preparation receipt explicitly
records `model_runs_performed:false` and `canonical_evaluation:false`.

## Verification performed on 2026-09-21

- Both selected native class imports passed with outbound networking blocked;
  optimizer construction was deliberately excluded because EoH probes the model.
- Both actual pinned provider implementations made exactly one request to an
  inert temporary HTTP fixture through real verified TLS and returned its fixed
  response. `check_heuristic_transport.py` blocks any other network destination,
  invokes no optimizer, and evaluates no generated program.
- Both native Python environments verified the deployed relay's certificate and
  received HTTP401 from an unauthenticated models request. This confirms local
  transport and authentication enforcement, not inference conformance.
- All 14 pure native plans and private control templates validated. Both source
  checkouts remained clean. No native research/model run was performed by this
  preparation task.

The initial public CA bundle SHA256 is
`6bb5f99a779485e3c07c423aec6239e6f0269e14cbd8312c81673be9985f35fd`.
Dependency-freeze hashes are
`30009be46f7cfd3cb6663ca5c2cabb93b6a8cbcd16e3fec3628bb8d8c0eb38a3`
(EoH) and
`8756ab562aa2c30c18439f561bcc3d3165b09e127163a9c81077219b1d706494`
(MEoH). Template-fragment hashes are
`d9db7952a094ecae258d8c888611ec4316087a0518d30b860bf8f132ac5aed1a`
and `47e0127df608ae92439b609cf19d71475ba465508cc0e56060fcaaceba9a9aee`,
respectively. Subsequent queue receipts capture the actual driver and input
hashes at launch.
