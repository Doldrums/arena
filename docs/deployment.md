# Deployment boundary

Empira's discovery board is deployed at
[research-arena.small-pine-3af7.workers.dev](https://research-arena.small-pine-3af7.workers.dev).
Cloudflare Access protects the entire Worker, including HTML, static assets and
API responses. The deployment serves registry data and an explicitly published
results snapshot; it does not connect to the separate live VM backend.

## What the Cloudflare deployment serves

| Route | Behavior after Access sign-in |
| --- | --- |
| `/` | Tasks overview and catalog |
| `/?view=participants` | Participants and research references |
| `/results` | Published results overview from `/api/results-overview` |
| `/experiments` | Experiment viewer page; `/api/runs` returns 503 `observer_not_connected` |
| `/experiments/results` | Private workspace page; `/api/control/results` is unavailable (404) |
| `/experiments/queue` or `/queue` | Queue page; live queue APIs are unavailable |

The published overview is bundled from `registry/results-overview.json`. Its
refresh control reloads that snapshot; new VM measurements require an explicit
publication and deployment. The overview does not send an Arena control key or
fall back to private control endpoints. Non-GET/HEAD requests return 405.

The existing private VM service hosts live experiments and control APIs
independently. This Worker has no VM proxy, live run ingestion, scheduler, D1 or
R2 bindings. Serving the workspace pages does not make their live APIs available
on the Cloudflare hostname.

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
3. Check `/api/health`, private `no-store` response headers, and the expected
   503/404 responses for unavailable experiment and control APIs. Confirm the
   discovery results page makes no private control request.
4. Confirm the Worker-level Access policy still applies and preview URLs remain
   disabled. Check that its allow rules contain only the `mbzuai.ac.ae` email
   domain and the explicit owner address, and that the login guidance is visible.

Deployments, registry updates, page loads and validation must never launch an
experiment. Billable runs require a separate authorized submission to the
private execution service with a concrete run specification and budget.
