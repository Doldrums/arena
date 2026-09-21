# Cloudflare experiment connection — 21 September 2026

## Cause

The deployed Cloudflare Worker served the experiment viewer but deliberately
returned `503 observer_not_connected` for `/api/runs` and 404 for `/api/stream`.
The viewer therefore never received its run list and remained on a blank loading
state. Authentication itself succeeded.

## Deployed correction

- Optional `OBSERVER` VPC Service proxy to the private VM observer, restricted to
  explicit read-only native routes. No queue/control API or launch capability.
- User authentication runs before every proxied request. Verified expiry from
  either Access or the temporary debug session bounds streaming responses.
- No browser credentials or arbitrary upstream headers are forwarded. Response
  caching and upstream redirect following are disabled.
- Initial viewer failures now display an unavailable state with a retry button;
  successful recovery clears the stale error and preserves existing data.
- A separate pinned connector binary and deployment service unit are installed.
  Existing VM board and execution services have not been restarted.

## Validation

- TypeScript check and 32 API tests pass, including native route restrictions,
  credential stripping, streaming cancellation, timeout and session expiry.
- All 29 dashboard tests pass, including three connection recovery scenarios.
- Fresh Chromium loaded the actual VM observer through the updated router using
  a loopback-only test binding: 14 experiment rows, the selected dashboard, and a
  program detail with saved source. SSE delivered snapshots/runtime updates and
  reconnected after 30 seconds. No browser errors or error banner remained.
- That local test exercised the actual observer data contract; authentication was
  separately covered by API tests.
- After deployment, fresh Chromium authenticated against the debug Worker and
  verified 14 real VM experiments, snapshot/program detail responses, secure
  cookie flags and private no-store responses. The event stream delivered two
  snapshots and 12 runtime events, reconnecting after 33 seconds. There were no
  browser errors or error banners. Writes returned 405; control routes 404;
  unauthenticated and logged-out observer requests returned 401.
- Main Access policy and login guidance were independently rechecked. The policy
  still permits only the university domain plus the owner address. The main
  authenticated UI was not exercised with a university OTP; its matching VPC
  binding and Access gate were verified separately.
- Independent source review found no release blocker.

## Rollout status

The user completed the additional OAuth grant. The private connector is healthy
with four QUIC connections. Public tunnel ingress is a catch-all 404 and no public
hostname or DNS record was created. The scoped HTTP VPC Service targets only
`127.0.0.1:8080`; both Worker configurations bind that same service as `OBSERVER`.

| Resource | Deployed identity |
| --- | --- |
| Private tunnel | `a05d53a0-4787-4c34-a3b4-b35d5026a089` (`empira-observer-vm`) |
| VPC Service | `01a0c45f-2f66-73d2-b574-803fcc32515e` (`empira-observer`) |
| Main Worker version | `787fe715-dc37-4c6e-bd1d-4864c845573a` |
| Debug Worker version | `16c07728-1c89-4546-bde9-fe13666977c7` |

`cloudflared` 2026.9.1 was checked against the official release SHA-256
`03f1f25d1cc93b9ad6c60569d44060bc4f17ed97075760ed8cfca4b12dcd68cc`.
The unit uses systemd's credentials-directory environment variable, compatible
with the installed VM systemd version. The temporary debug code and its cutoff
remain unchanged. Neither secrets nor generated program source are in this report.

The 14 native VM runs are distinct from the 165 archived research experiments in
the published overview. This fix connects the current VM observer; it does not
silently copy the local archive or launch additional experiments.
