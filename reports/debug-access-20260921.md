# Temporary debug access — 21 September 2026

Update: the subsequent [observer connection](observer-connection-20260921.md)
also enables authenticated native experiment inspection. The version and initial
verification below document the original deployment; the code and cutoff are unchanged.

The user requested a code-based login for reviewers without a university email,
using an email-style form. The separately deployed debug Worker provides access
to the catalog and published results. It does not expose experiment controls or
connect to the private VM backend.

## Deployment

- URL: https://research-arena-debug.small-pine-3af7.workers.dev
- Worker: `research-arena-debug`
- Version: `48efaaae-56c8-4f1c-8f5d-464028f2c105`
- Entry point: `api/src/debug.ts`; config: `api/wrangler.debug.jsonc`
- Global cutoff: 22 September 2026, 13:44:51 UTC / 17:44:51 Dubai.
- Session duration: at most one hour, never beyond the global cutoff.
- One randomly generated access code is reusable within the debug window. Only
  its SHA-256 digest is deployed, alongside a separate signing secret. Neither
  the code nor these secrets are included in the repository or this report.

The main Worker continues to use Cloudflare Access. Its policy allows all
`@mbzuai.ac.ae` addresses and retains the owner address. Entering an allowed email
in the debug form continues to that existing Access login; it does not grant a
debug session. Preview URLs and debug Worker observability are disabled.

## Validation

- TypeScript check and all 17 API tests passed.
- Debug Worker dry run passed.
- An independent source review found no release blocker or live credentials in
  the changed files.
- A fresh Chromium session against the deployed Worker verified that unauthenticated
  pages redirect to login and the results API returns 401. An incorrect code was
  rejected; the real code authenticated successfully using native Workers crypto.
- The issued cookie was Secure, HttpOnly and SameSite=Lax. Authenticated API and
  asset responses prohibit caching. Control mutations returned 405.
- Results displayed five research rows. The API returned 165 research experiments,
  196 integration runs and 110 native results. These counts describe distinct
  evidence categories and are not combined into a performance claim.
- Task families displayed the 12 scientific domain groups. Opening login with a
  valid session returned to the board. Email continuation reached the university
  Access login. Logging out removed access in that browser. No browser errors were
  observed and no OTP email or experiment was triggered.

The first browser test exposed a form-origin issue caused by `no-referrer`.
The deployed fix uses `Referrer-Policy: same-origin`; exact-origin POST validation
remains enforced. The complete browser flow passed after redeployment.

The fixed deadline disables all requests automatically. Deleting the temporary
Worker is a separate cleanup action. To revoke sessions early, rotate the signing
secret or move the global cutoff into the past; rotating the access code alone
does not revoke existing sessions. See [debug access operations](../docs/debug-access.md).
