# Temporary debug entry

`api/src/debug.ts` is a separate Worker for a short, explicitly enabled debug window at
`https://research-arena-debug.small-pine-3af7.workers.dev`. The production entrypoint
and Cloudflare Access policy are unchanged. It serves the existing catalog, published
results, and web assets through the same read-only router, with no control backend.
An optional private `OBSERVER` VPC Service binding also permits native experiment
inspection. Observer streams inherit the verified cookie/global expiry and close
after at most 30 seconds, requiring a newly authenticated request to reconnect.

Use `api/wrangler.debug.jsonc` explicitly for every debug Wrangler operation. Its
asset directory `../web` is relative to that config file. The template names only
`research-arena-debug`, disables preview URLs and observability, runs authentication
before every asset, and defaults to an expired window.

Before an authorized deployment, configure:

- `DEBUG_ACCESS_CODE_HASH`, a secret binding containing the lowercase, 64-character
  SHA-256 hex digest of one externally generated, high-entropy code (at least 32
  random base64url characters). Never place the code or digest in a committed file.
- `DEBUG_SESSION_SECRET`, a separate secret binding generated from at least 32
  random bytes, encoded as unpadded base64url or hex (43–256 characters). Rotating
  this secret invalidates all sessions. Do not reuse the code or its digest.
- `DEBUG_ACCESS_EXPIRES_AT`, an absolute Unix timestamp in **seconds**, expressed
  as a 10-digit string. Set it to the agreed end of the short debug window, normally
  24 hours after activation. ISO dates and millisecond timestamps are rejected.
- `DEBUG_LOGIN_RATE_LIMITER`, the Cloudflare binding already defined in the config:
  10 login attempts per connecting IP per 60 seconds. Namespace `2026092101` is
  reserved for this debug binding; check account uniqueness before deployment.

Missing or malformed settings fail closed. The global deadline gates all requests,
including existing sessions and the login page. A session lasts at most one hour
and never beyond that deadline. Cookies use `__Host-`, `Secure`, `HttpOnly`,
`SameSite=Lax`, and `Path=/`; their HMAC binds the exact debug origin and signed
version, issue time, and expiry. Only the configured debug HTTPS origin is accepted.

Enter the code in the login form; never put it in a URL. An `@mbzuai.ac.ae` email
or the exact owner address `contact@amoriodi.xyz` only redirects to the fixed primary
Access sign-in. It does not authenticate a debug session. The form never echoes the
submitted value. All responses, including assets and errors, prohibit caching.

`POST /logout` with an `Origin` header matching the debug origin clears this browser's
cookie. Clearing a stateless cookie does not revoke copies of it; rotate the session
secret or expire the global window to revoke all sessions. Delete the separate debug
Worker after the debug window; do not extend the primary entrypoint with this code.

Local validation, with synthetic credentials only:

```sh
npm run typecheck
npm run test:api
npx wrangler deploy --config api/wrangler.debug.jsonc --dry-run --outdir /tmp/empira-debug-dry-run
```

The rate limit is a per-location abuse brake, not an exact global quota; the random
code and absolute expiry remain required. See Cloudflare's official
[rate-limit binding documentation](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/)
and [native timing-safe comparison](https://developers.cloudflare.com/workers/runtime-apis/web-crypto/#timingsafeequal).
