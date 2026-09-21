# Private Codex provider gateway

`python -m arena.providers` provides a loopback compatibility service for native
research frameworks whose SDKs expect OpenAI endpoints. Its upstream is fixed to
`https://chatgpt.com/backend-api/codex`; it uses the operator-supplied account JWT.
This is a private compatibility integration, not the public OpenAI API or a
promise that every public API option is supported by the account endpoint.

Importing the module, opening Arena, or validating its registry never reads a
credential or starts a generation. Model discovery and serving require explicit
operator commands. No model ID is substituted or aliased.

## Credentials and launch

Keep the JWT outside the repository in a regular file owned by the gateway
service user with mode `0600`. The file may contain the JWT alone or the supplied
attachment text containing exactly one JWT. The gateway reads it for each
upstream request, so replacing the private file rotates credentials without
restarting the process. Expired credentials are rejected. The locally decoded
expiry is informational; upstream remains responsible for JWT authentication.
No account ID, email, token, prompt or response text is logged.

Run the gateway under a **different Unix identity from research workers**. A
`0600` JWT is not isolated from arbitrary code running under its owner's UID.
Workers need only a separate local gateway key and the loopback URL; they must
not be able to read the upstream credential file.

Generate the independent gateway key without writing its value to stdout:

```sh
python -m arena.providers key --file /private/service/gateway-key
```

The destination must not already exist; it is created with mode `0600`. Then:

```sh
python -m arena.providers serve \
  --token-file /private/service/codex-jwt \
  --gateway-key-file /private/service/gateway-key \
  --port 8789 \
  --max-concurrency 2 \
  --requests-per-minute 20 \
  --timeout 180 \
  --allowed-model gpt-5.6-sol
```

This example selects an exact discovery-listed model, not a generation-verified
model recommendation. The service binds to `127.0.0.1`; wildcard/public binds
are refused. Never expose the gateway directly to the browser or public network.
An authorized worker uses `http://127.0.0.1:8789/v1` as its OpenAI `base_url` and
the separate gateway key as its SDK `api_key`. Load that key through the worker's
private environment/secret mechanism, not a command-line argument or public run
specification. Gateway keys are scoped to this service instance, its optional
model allowlist, and its rate/concurrency policy; they are not upstream JWTs.
The queue/service is responsible for issuing per-run access and recording who
is authorized to use the gateway.

`--timeout` accepts 1–900 seconds. There are no automatic upstream retries.
Native SDKs may independently retry: configure and record their retry policy.
The concurrency limit bounds admitted generations, while the RPM limit counts
admitted requests (including failed upstream attempts). Busy/rate-limited
requests return `429` and `Retry-After`; invalid/expired upstream authorization
returns a sanitized `503`. Output streams are limited to 32 MiB, each SSE event
to 2 MiB, and request bodies to 2 MiB. A read timeout/stream deadline aborts the
upstream socket. Connection establishment also uses a bounded socket timeout.
Closing an HTTP connection does not prove cancellation of provider-side compute.

## Discovery and observed account access

```sh
python -m arena.providers models --token-file /private/service/codex-jwt
```

This prints sanitized model metadata and credential expiry, not account claims.
The HTTP equivalent is authenticated `GET /v1/models`; its results are cached
for up to five minutes. Discovery distinguishes `visibility: list` and `hide`;
a hidden listing is not evidence that a model is appropriate or approved for a
research batch. Every returned entry is labeled
`availability: listed_by_account_provider`, `generation_verified: false`.

On 2026-09-21 the explicitly supplied account credential returned HTTP 200 from
`/backend-api/codex/models?client_version=0.155.1`, listing:

| Exact ID | Visibility | Evidence |
| --- | --- | --- |
| `gpt-5.6-sol` | list | Account discovery |
| `gpt-5.6-terra` | list | Account discovery |
| `gpt-5.6-luna` | list | Account discovery |
| `gpt-6-astra` | list | Account discovery |
| `gpt-5.5` | list | Account discovery |
| `gpt-reserve` | hide | Account discovery |
| `codex-auto-review` | hide | Account discovery |

The one authorized tiny `gpt-5.4` request returned HTTP 400 indicating that model
was unsupported on this account endpoint. No replacement model was called.
The supplied credential's expiry was 2026-09-25 09:05:37 UTC. These are dated
observations, not permanent availability claims or successful generation tests
for the listed models. Repeat discovery after rotating credentials.

## Compatibility contract

All upstream generation requests use `store:false`, `stream:true`, and a string
`instructions` field. Caller `store:true` is rejected. Public Responses and Chat
Completions schemas are described by the
[official Responses API documentation](https://developers.openai.com/api/docs/guides/responses)
and [streaming documentation](https://developers.openai.com/api/docs/guides/streaming-responses).
Those documents do not establish support for individual parameters on this
private account endpoint; backend rejections remain explicit errors.

Supported local routes:

| Route | Behavior |
| --- | --- |
| `GET /v1/models` | Exact account discovery IDs, visibility, reasoning efforts and bridge capabilities. |
| `POST /v1/responses` | Text/input-item requests; Responses SSE passthrough or completed response JSON. |
| `POST /v1/chat/completions` | Text/image content, system/developer instructions, assistant function calls, tool results, function definitions/choice, reasoning effort, structured-output mapping, streaming or completed JSON. |
| `POST /v1/messages` | Nonstreaming Anthropic Messages text/function-tool compatibility; accepts the local key in `x-api-key` or Bearer authorization. |

Chat system/developer text is combined into upstream instructions in original
order. Function tools are translated to native Responses function tools;
arguments and per-call IDs are preserved. Only `n=1` is accepted. Responses
history must be supplied in `input`; stored response/conversation continuation
is not implemented. Image URLs are passed to upstream, not fetched by the
bridge. Audio, hosted-tool Chat mappings, background execution, arbitrary API
fields, and model aliases are not supplied.

The SSE parser handles chunk boundaries, UTF-8, CRLF, multiline data and comments.
An upstream failure/incomplete response or EOF without `response.completed`
cannot become a successful completion. Before streaming starts it returns a
sanitized HTTP error; after streaming starts it emits an error event and closes
without a success terminal marker. Chat function argument deltas and final
arguments are checked for consistency. `stream_options.include_usage` requests
the final Chat usage chunk. Token usage comes from the provider; absent counters
remain unrecorded, never assumed to be a zero-cost generation.

Messages compatibility rejects streaming, thinking/signature blocks,
Anthropic-specific caching fields, and unsupported tool/content types before
calling upstream. Native DGM additionally dispatches providers by model-name
prefix; its provider dispatch must be adapted explicitly to use a GPT model.
Pointing the Anthropic SDK at this gateway alone does not change that native
branching or justify pretending a Claude model is a GPT model.

## Explicit generation-control policy

The default `strict` policy rejects generation controls this private endpoint
does not guarantee: `temperature`, `top_p`, `top_k`, `max_tokens`,
`max_completion_tokens`, `max_output_tokens`, `stop`, frequency/presence penalties,
`seed`, and `logit_bias`. It does not silently discard them.

Many native frameworks always send temperature and token limits. The operator
can opt into the account's native generation behavior:

```sh
python -m arena.providers serve \
  --token-file /private/service/codex-jwt \
  --gateway-key-file /private/service/gateway-key \
  --compatibility-policy codex-native
```

Under this policy the known controls are validated and deliberately omitted.
Responses carry `X-Arena-Compatibility-Policy` and
`X-Arena-Unenforced-Controls` headers, plus `arena_compatibility` metadata in the
JSON/initial Chat SSE chunk or native Responses events. `/v1/models` also
advertises the active policy. This includes `compute_cap_enforced:false`.
For Messages, `stop_sequences` maps to the reported `stop` control.

A framework's `max_tokens:8192` is **not** a provider compute/token cap under this
policy. Temperature, stops, seeded sampling and penalties are likewise not
preserved. The study/run manifest must record this policy and every omitted
control; such a run cannot claim exact replication of those settings. Use
explicit request-count, wall-time and worker resource bounds independently.
No automatic probe or fallback is made to test alternate controls/models.

## Logging and verification

Each POST log contains only a generated request ID, validated model ID, observed
token counters and numeric status, plus a fixed error code on failure. The code
distinguishes local concurrency (`gateway_busy`), local request rate
(`gateway_rate_limit`) and account rate limits (`upstream_rate_limit`). It does
not include the upstream error message. Upstream HTTP bodies/errors, authorization
headers, decoded account claims and prompts are never included. Streaming
request content is returned only to the authenticated caller. The service sets
`Cache-Control:no-store`, refuses browser-origin requests and follows no
upstream redirects.

```sh
python -m pytest -q tests/test_providers.py
```

Tests use controlled fixture providers and local sockets: role/tool translation,
SSE fragmentation, completion/error handling, private credentials and expiry,
explicit compatibility metadata, exact model selection, gateway authentication,
concurrency/rate rejection and interrupted stream deadlines. They make no real
model calls. The live discovery and the rejected `gpt-5.4` smoke described above
were separate, explicitly authorized checks.
