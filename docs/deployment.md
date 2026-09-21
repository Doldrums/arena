# Deployment boundary

Empira's discovery board is deployed at
[research-arena.small-pine-3af7.workers.dev](https://research-arena.small-pine-3af7.workers.dev).
Cloudflare Access protects the entire Worker, including HTML, static assets and
API responses. Registry data and the published results overview are bundled with
the Worker. Native experiment inspection can connect to the private VM through
the optional `OBSERVER` VPC Service binding described below.

## What the Cloudflare deployment serves

| Route | Behavior after Access sign-in |
| --- | --- |
| `/` | Tasks overview and catalog |
| `/?view=participants` | Participants and research references |
| `/results` | Published results overview from `/api/results-overview` |
| `/experiments` | Live read-only experiment viewer when `OBSERVER` is configured; otherwise the page shows an unavailable/retry state |
| `/experiments/results` | Private workspace page; `/api/control/results` is unavailable (404) |
| `/experiments/queue` or `/queue` | Queue page; live queue APIs are unavailable |

The published overview is bundled from `registry/results-overview.json`. Its
refresh control reloads that snapshot; new VM measurements require an explicit
publication and deployment. The overview does not send an Arena control key or
fall back to private control endpoints. Non-GET/HEAD requests return 405.

The existing private VM service hosts experiments and control APIs independently.
The Worker exposes only an explicit allowlist of native observer GET/HEAD routes.
Queue/control routes remain unavailable, and all mutations return 405. Connecting
the observer does not launch experiments or enable private execution controls.

## Private experiment connection

Create a remotely managed Cloudflare Tunnel without a public hostname or DNS
record. Its public ingress must be a catch-all `http_status:404`. Use a
`cloudflared` connector at version 2025.7.0 or later with QUIC transport; the
deployment unit pins 2026.9.1 at `/usr/local/lib/arena/cloudflared-2026.9.1`.
Verify the binary against the official release checksum before installation.

Install `scripts/deployment/arena-observer-tunnel.service` on the VM. Store the
tunnel token at `/etc/arena-observer-tunnel/token`, owned by root with mode 0600
inside a root-only directory. The unit loads this token through systemd
credentials rather than command-line arguments. The board continues to listen
only on `127.0.0.1:8080`; it must not be exposed as a public HTTP origin.

Register one HTTP VPC Service targeting **127.0.0.1, port 8080**, through that
tunnel. Bind its actual service ID as `OBSERVER` in both Worker configurations:

```json
"vpc_services": [{"binding": "OBSERVER", "service_id": "<registered-service-id>"}]
```

VPC Service configuration fixes the destination; a public request cannot choose
another host or port. Do not substitute a VPC Network binding. The Worker creates
a new upstream request without browser cookies, bearer credentials or Access
headers. It rejects unknown route shapes, query parameters and upstream redirects.
Only native run list/snapshot/detail routes and `/api/stream` are proxied. All
responses prohibit caching. Header retrieval is limited to 10 seconds; response
streams close after 30 seconds or verified authentication expiry, whichever is
earlier. The browser reconnects through authentication for subsequent updates.

Cloudflare provisioning requires Tunnel edit and Connectivity Directory admin
permissions, in addition to Worker deployment permissions. Code and local browser
checks are prepared as of 21 September 2026; enabling the production binding is
pending the corresponding OAuth grant. See the connection report for rollout status.

See the official [Workers VPC setup](https://developers.cloudflare.com/workers-vpc/get-started/)
and [connector requirements](https://developers.cloudflare.com/workers-vpc/configuration/tunnel/).

For local inspection, `python -m arena --root ...` reads native journals and
heartbeat files. `npm run dev:cloudflare` uses a separate loopback-only Worker
entrypoint with the same registry routes and Cloudflare backend limitations.

## Access and deployment

The Worker is `research-arena`. Its Access organization is
`empira-research.cloudflareaccess.com`; a Worker-level policy protects all
traffic and allows all email addresses at the exact `mbzuai.ac.ae` domain, plus
the existing explicitly approved owner address. One-time PIN login is enabled.
The login page says: "Sign in with your @mbzuai.ac.ae email. We'll send you a
one-time code." The `workers.dev` hostname is enabled; preview URLs remain
disabled.

`ACCESS_TEAM_DOMAIN` is `https://empira-research.cloudflareaccess.com`.
`ACCESS_AUD` must match the Access application's audience tag, not its application
UUID. Preserve both settings when deploying:

```sh
npx wrangler deploy --keep-vars
```

`api/src/index.ts` verifies the Access JWT signature, issuer, audience, expiration
and required identity claims before routing any request. Static assets run the
Worker first. Missing configuration returns 503; missing or invalid tokens
return 401 or 403 when a request reaches the Worker. The Access edge normally
redirects unauthenticated browser requests to sign-in. No production Access
bypass variable is supported.

See Cloudflare's [Access JWT verification](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
and [Worker Access protection](https://developers.cloudflare.com/workers/configuration/cloudflare-access/)
documentation.

## Postdeployment checks

1. Without an Access session, confirm `/`, `/results`, a static JavaScript asset
   and `/api/results-overview` reveal no board or results content.
2. With an allowed session, open Tasks, Participants and Results; confirm assets
   load and the overview matches the published registry snapshot.
3. Check `/api/health` and private `no-store` response headers. With `OBSERVER`
   configured, verify run selection, a native detail view, and SSE reconnection.
   Without the binding, observer routes return 503; control APIs always return
   404. Confirm the discovery results page makes no private control request.
4. Confirm the Worker-level Access policy still applies and preview URLs remain
   disabled. Check that its allow rules contain only the `mbzuai.ac.ae` email
   domain and the explicit owner address, and that the login guidance is visible.

Deployments, registry updates, page loads and validation must never launch an
experiment. Billable runs require a separate authorized submission to the
private execution service with a concrete run specification and budget.
