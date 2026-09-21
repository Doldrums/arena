# Cloudflare publication — 2026-09-21

The user authorized deployment and selected the default Cloudflare hostname
without a custom domain.

- Site: https://research-arena.small-pine-3af7.workers.dev
- Results: https://research-arena.small-pine-3af7.workers.dev/results
- Worker: `research-arena`
- Current version: `99cf0c9a-a0b4-424f-ad23-9a97c7283b83`
- Application content: commit `cbcb091c58c5d5df236f86a8d60c805da6d34cc6`.
- Published measurements: 196 integration runs, 131 integration outcomes,
  and 165 separate SCiEL research observations.

The account had no existing Arena Worker or Access organization. Deployment
created the Worker, the Empira Access organization, an email one-time-PIN login
provider and a Worker-level Access application. The policy permits only the
`mbzuai.ac.ae` email domain and the existing explicit external owner address,
following the user's request to enable university-wide login. The domain rule
has no wildcard or additional domains. Other Workers are unchanged. No paid
subscription or experiment was started.

The organization's login header now reads: "Sign in with your @mbzuai.ac.ae
email. We'll send you a one-time code." Email one-time PIN remains the
application's only allowed identity provider.

The committed Wrangler configuration now pins the account, enables this
`workers.dev` address and sets the non-secret Access issuer and audience.
Preview URLs remain disabled. OAuth credentials are outside the repository.
All static assets still run through the production JWT-verifying Worker.

## Verification

- `wrangler deploy --keep-vars` uploaded the assets and activated the version.
- Remote deployment metadata matches the version above. Remote Access bindings
  match `wrangler.jsonc`; the production subdomain is enabled and previews disabled.
- Unauthenticated browser-style requests to `/`, `/results`,
  `/api/results-overview` and `/arena-results-overview.js` return 302 to the
  configured Access login host, with the correct application audience.
- Chromium reached the Empira login form and found the email input. No login
  code was requested or consumed by the agent.
- Remote policy readback confirms exactly the university email-domain rule and
  the existing external owner address. The application's Worker destination,
  identity provider, session duration and other settings are preserved.
- Fresh HTTP and Chromium sessions reached the Access login page. Chromium
  confirmed the university email guidance and email input are visible; the
  screenshot was inspected. Other organization settings are preserved; the API
  omitted an empty `trusted_accounts` array.
- Nine Worker API tests passed after configuration changes. The application
  content had already passed desktop/mobile and numeric-results verification
  before upload.
- Authenticated production rendering was not exercised: that requires the
  owner's email PIN. Local application rendering and production access gating
  were checked separately.

The Worker serves the catalog and published results snapshot. Live experiment
control and queue APIs remain on the separate private VM; this deployment does
not proxy those APIs. See `docs/deployment.md` for the route boundaries.
