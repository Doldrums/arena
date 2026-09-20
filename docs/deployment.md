# Deployment boundary — milestone 1

This repository includes a locally runnable board and a buildable Cloudflare Worker. It has **not been deployed**. D1, R2, the Vast supervisor, cloud run ingestion and paid experiment execution are not implemented in this milestone.

## Two current server modes

| Mode | Catalog / participants | Native SCiEL experiments | Authentication |
| --- | --- | --- | --- |
| `python -m arena --root ...` | Offline registry snapshot | Reads local journals and heartbeat files | Loopback only |
| `npm run dev:cloudflare` | Same registry JSON | HTTP 503 `observer_not_connected` | Separate loopback-only development entrypoint |
| Production Worker build | Same registry JSON | HTTP 503 `observer_not_connected` | Cloudflare Access JWT verification, required before HTML/assets/API |

The two servers deliberately expose the same catalog and participant response shapes. The Python server is a migration observer and local development tool, not the future cloud execution scheduler.

## Production configuration when deployment is requested

Create a Cloudflare Access application restricted to the team's identities. Set `ACCESS_TEAM_DOMAIN` to its `https://<team>.cloudflareaccess.com` origin and `ACCESS_AUD` to that application's audience. Add the intended custom hostname/route after the Access policy exists. `workers_dev` and preview URLs are disabled in the committed configuration.

`api/src/index.ts` validates signature, issuer, audience, expiration and required identity claims. A request header alone is not authentication. All assets invoke the Worker first; missing Access configuration yields 503 and missing/invalid tokens yield 401/403. No Access bypass variable is accepted in the production entrypoint. `api/src/dev.ts` is explicitly for local development and rejects non-loopback request hostnames.

The implementation follows Cloudflare's [Access JWT verification](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/) and [Worker asset binding](https://developers.cloudflare.com/workers/static-assets/binding/) documentation.

## Next cloud slice

Introduce D1 migrations for immutable revisions, run requests, lease generations and state transitions. Add R2 artifact manifests and scoped upload receipts. Only then connect the authenticated outbound-polling supervisor on a Vast VM. Native framework processes retain their native loop; the supervisor owns environment isolation, resource limits and artifact delivery.

A merged registry PR updates metadata. It must never implicitly start a billable experiment. Starting a run will require a separate team-authorized action against a concrete immutable RunSpec and budget.
