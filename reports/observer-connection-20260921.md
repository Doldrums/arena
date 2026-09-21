# Cloudflare experiment connection — 21 September 2026

## Cause

The deployed Cloudflare Worker served the experiment viewer but deliberately
returned `503 observer_not_connected` for `/api/runs` and 404 for `/api/stream`.
The viewer therefore never received its run list and remained on a blank loading
state. Authentication itself succeeded.

## Prepared correction

- Optional `OBSERVER` VPC Service proxy to the private VM observer, restricted to
  explicit read-only native routes. No queue/control API or launch capability.
- User authentication runs before every proxied request. Verified expiry from
  either Access or the temporary debug session bounds streaming responses.
- No browser credentials or arbitrary upstream headers are forwarded. Response
  caching and upstream redirect following are disabled.
- Initial viewer failures now display an unavailable state with a retry button;
  successful recovery clears the stale error and preserves existing data.
- A separate pinned connector binary and deployment service unit are prepared.
  Existing VM board and execution services have not been restarted.

## Validation

- TypeScript check and 32 API tests pass, including native route restrictions,
  credential stripping, streaming cancellation, timeout and session expiry.
- All 29 dashboard tests pass, including three connection recovery scenarios.
- Fresh Chromium loaded the actual VM observer through the updated router using
  a loopback-only test binding: 14 experiment rows, the selected dashboard, and a
  program detail with saved source. SSE delivered snapshots/runtime updates and
  reconnected after 30 seconds. No browser errors or error banner remained.
- The test exercised the actual observer data contract; authentication was
  separately covered by API tests. It does not claim production connectivity.
- Independent source review found no release blocker.

## Rollout status

Live deployment is pending a Cloudflare OAuth grant for Tunnel and Connectivity
Directory access. Existing Worker deployment credentials were rejected by the
Connectivity API with authentication error 10000. No public origin or permissive
fallback has been created. After authorization, create the private tunnel/service,
bind it to both Workers, and repeat the authenticated browser checks on Cloudflare.

The 14 native VM runs are distinct from the 165 archived research experiments in
the published overview. This fix connects the current VM observer; it does not
silently copy the local archive or launch additional experiments.
