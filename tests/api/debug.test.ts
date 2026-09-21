import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createHash, createHmac, timingSafeEqual} from 'node:crypto';
import debug, {type DebugEnv} from '../../api/src/debug.ts';
import {route} from '../../api/src/router.ts';

// Node lacks this documented Workers-native extension. Keep the shim in tests only.
Object.defineProperty(crypto.subtle, 'timingSafeEqual', {value: timingSafeEqual, configurable: true});
const ORIGIN = 'https://research-arena-debug.small-pine-3af7.workers.dev';
const PRIMARY_URL = 'https://research-arena.small-pine-3af7.workers.dev/';
const COOKIE = '__Host-empira_debug';
// Fixed synthetic fixtures only; these are never deployed or used as real credentials.
const CODE = 'unit-test-fixture-only-0123456789';
const SECRET = 'unit-test-session-fixture-only-0123456789-abcdefgh';
const HASH = createHash('sha256').update(CODE).digest('hex');
const now = () => Math.floor(Date.now() / 1000);
const request = (path: string, init?: RequestInit) => new Request(`${ORIGIN}${path}`, init);
const environment = (overrides: Partial<DebugEnv> = {}): DebugEnv => ({
  ASSETS: {fetch: async req => new Response(`asset:${new URL(req.url).pathname}`, {headers: {'Cache-Control': 'public, max-age=86400', ETag: 'asset-tag'}})},
  DEBUG_ACCESS_CODE_HASH: HASH,
  DEBUG_SESSION_SECRET: SECRET,
  DEBUG_ACCESS_EXPIRES_AT: String(now() + 24 * 3600),
  DEBUG_LOGIN_RATE_LIMITER: {limit: async () => ({success: true})},
  ...overrides,
});
const formRequest = (credential = CODE, headers: Record<string, string> = {}, path = '/login') => request(path, {
  method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded', Origin: ORIGIN, ...headers},
  body: new URLSearchParams({credential}),
});
const cookieValue = (response: Response) => response.headers.get('Set-Cookie')!.split(';')[0];
function signedCookie(iat: number, exp: number, origin = ORIGIN, secret = SECRET): string {
  const claims = `v1.${iat}.${exp}`;
  const signature = createHmac('sha256', secret).update(`empira-debug:${origin}:${claims}`).digest('base64url');
  return `${COOKIE}=${claims}.${signature}`;
}
function assertPrivate(response: Response): void {
  assert.equal(response.headers.get('Cache-Control'), 'private, no-store, max-age=0');
  assert.equal(response.headers.get('CDN-Cache-Control'), 'no-store');
  assert.equal(response.headers.get('Cloudflare-CDN-Cache-Control'), 'no-store');
  assert.equal(response.headers.get('Referrer-Policy'), 'same-origin');
  assert.equal(response.headers.get('ETag'), null);
}

test('debug protects every asset and API before calling the existing read-only router', async () => {
  let assets = 0;
  const env = environment({ASSETS: {fetch: async () => {assets++; return new Response('secret asset');}}});
  for (const path of ['/', '/results', '/style.css', '/arena-atlas.js', '/index.html', '/private.json', '/not-found']) {
    const response = await debug.fetch(request(path), env);
    assert.equal(response.status, 303);
    assert.equal(response.headers.get('Location'), '/login');
    assertPrivate(response);
    assert.equal(await response.text(), '');
  }
  for (const path of ['/api', '/api/catalog', '/api/results-overview', '/api/runs', '/api/control/results']) {
    const response = await debug.fetch(request(path), env);
    assert.equal(response.status, 401);
    assert.match(response.headers.get('Content-Type')!, /application\/json/);
    assert.deepEqual(await response.json(), {error: 'authentication_required'});
    assertPrivate(response);
  }
  assert.equal(assets, 0);
  const page = await debug.fetch(request('/login'), env);
  assert.equal(page.status, 200);
  assertPrivate(page);
  const csp = page.headers.get('Content-Security-Policy')!;
  assert.ok(csp.includes(`form-action 'self' ${PRIMARY_URL} https://empira-research.cloudflareaccess.com;`));
  assert.equal(csp.includes('*'), false);
  const html = await page.text();
  assert.match(html, /Email or access code/);
  assert.match(html, /method="post" action="\/login"/);
  assert.match(html, /name="credential" type="text"/);
  assert.equal((await debug.fetch(request('/login', {method: 'HEAD'}), env)).status, 200);
  assert.equal(await (await debug.fetch(request('/login', {method: 'HEAD'}), env)).text(), '');
});

test('missing, malformed, or expired configuration fails closed including login and valid sessions', async () => {
  const validCookie = signedCookie(now(), now() + 300);
  const invalid: Partial<DebugEnv>[] = [
    {DEBUG_ACCESS_CODE_HASH: undefined}, {DEBUG_ACCESS_CODE_HASH: 'bad'},
    {DEBUG_SESSION_SECRET: undefined}, {DEBUG_SESSION_SECRET: 'short'}, {DEBUG_SESSION_SECRET: HASH},
    {DEBUG_ACCESS_EXPIRES_AT: undefined}, {DEBUG_ACCESS_EXPIRES_AT: '2026-09-22T00:00:00Z'},
    {DEBUG_ACCESS_EXPIRES_AT: String(Date.now())}, {DEBUG_ACCESS_EXPIRES_AT: 'Infinity'},
    {DEBUG_LOGIN_RATE_LIMITER: undefined},
  ];
  for (const bad of invalid) for (const path of ['/login', '/', '/api/catalog', '/arena-atlas.js']) {
    const response = await debug.fetch(request(path, {headers: {Cookie: validCookie}}), environment(bad));
    assert.equal(response.status, 503);
    assert.deepEqual(await response.json(), {error: 'debug_access_not_configured'});
    assertPrivate(response);
  }
  const expired = environment({DEBUG_ACCESS_EXPIRES_AT: String(now() - 1)});
  for (const path of ['/login', '/logout', '/', '/results', '/api/results-overview', '/arena-atlas.js']) {
    const response = await debug.fetch(request(path, {headers: {Cookie: validCookie}}), expired);
    assert.equal(response.status, 403);
    assert.deepEqual(await response.json(), {error: 'debug_access_expired'});
  }
  assert.equal((await debug.fetch(formRequest(), expired)).status, 403);
});

test('login accepts only POST form credentials with a matching origin and bounded body', async () => {
  const env = environment();
  for (const origin of ['', 'null', 'https://attacker.example', `${ORIGIN}.attacker.example`]) {
    const response = await debug.fetch(formRequest(CODE, {Origin: origin}), env);
    assert.equal(response.status, 403);
    assert.equal(response.headers.get('Set-Cookie'), null);
  }
  assert.equal((await debug.fetch(formRequest(CODE, {'Sec-Fetch-Site': 'cross-site'}), env)).status, 403);
  const missingOrigin = formRequest();
  missingOrigin.headers.delete('Origin');
  assert.equal((await debug.fetch(missingOrigin, env)).status, 403);
  for (const credential of ['', 'wrong-code', CODE + 'x', 'name@untrusted.example']) {
    const response = await debug.fetch(formRequest(credential), env);
    assert.ok(response.status === 400 || response.status === 401);
    assert.equal(response.headers.get('Set-Cookie'), null);
    assert.equal(response.headers.get('Location'), null);
  }
  const invalidHeaders: Record<string, string>[] = [{'Content-Type': 'application/json'}, {'Content-Length': '999999'}];
  for (const headers of invalidHeaders) {
    assert.equal((await debug.fetch(formRequest(CODE, headers), env)).status, 400);
  }
  const oversized = formRequest('x'.repeat(2048));
  assert.equal(oversized.headers.get('Content-Length'), null); // Verify the stream limit, too.
  assert.equal((await debug.fetch(oversized, env)).status, 400);
  const duplicate = request('/login', {method: 'POST', headers: {Origin: ORIGIN, 'Content-Type': 'application/x-www-form-urlencoded'}, body: `credential=${CODE}&credential=${CODE}`});
  assert.equal((await debug.fetch(duplicate, env)).status, 400);
  assert.equal((await debug.fetch(request('/login?credential=' + CODE), env)).headers.get('Set-Cookie'), null);
  assert.equal((await debug.fetch(request('/login', {method: 'PUT'}), env)).status, 405);
});

test('login issues a secure bounded cookie and serves exactly the existing results and catalog', async () => {
  const env = environment();
  const response = await debug.fetch(formRequest(CODE, {}, '/login?next=https://attacker.example'), env);
  assert.equal(response.status, 303);
  assert.equal(response.headers.get('Location'), '/');
  assertPrivate(response);
  const setCookie = response.headers.get('Set-Cookie')!;
  for (const flag of ['Path=/', 'HttpOnly', 'Secure', 'SameSite=Lax', 'Max-Age=3600']) assert.ok(setCookie.includes(flag));
  assert.equal(setCookie.includes('Domain='), false);
  const exposed = [...response.headers].flat().join(' ') + await response.text();
  for (const secret of [CODE, SECRET, HASH]) assert.equal(exposed.includes(secret), false);
  const cookie = cookieValue(response);
  for (const method of ['GET', 'HEAD']) {
    const existingSession = await debug.fetch(request('/login', {method, headers: {Cookie: cookie}}), env);
    assert.equal(existingSession.status, 303);
    assert.equal(existingSession.headers.get('Location'), '/');
  }
  const claims = cookie.split('=')[1].split('.');
  assert.equal(claims[0], 'v1');
  assert.equal(Number(claims[2]) - Number(claims[1]), 3600);
  for (const path of ['/api/results-overview', '/api/catalog', '/api/participants', '/api/search-families']) {
    const result = await debug.fetch(request(path, {headers: {Cookie: cookie}}), env);
    assert.equal(result.status, 200);
    assertPrivate(result);
    assert.deepEqual(await result.json(), await (await route(request(path), env)).json());
  }
  for (const [path, asset] of [['/', '/index.html'], ['/results', '/results.html'], ['/arena-atlas.js', '/arena-atlas.js']]) {
    const result = await debug.fetch(request(path, {headers: {Cookie: cookie}}), env);
    assert.equal(result.status, 200);
    assertPrivate(result);
    assert.equal(await result.text(), `asset:${asset}`);
  }
  assert.equal(await (await debug.fetch(request('/results', {method: 'HEAD', headers: {Cookie: cookie}}), env)).text(), '');
  assert.equal((await debug.fetch(request('/api/control/results', {headers: {Cookie: cookie}}), env)).status, 404);
  assert.equal((await debug.fetch(request('/api/runs', {headers: {Cookie: cookie}}), env)).status, 503);
  for (const method of ['POST', 'PUT', 'PATCH', 'DELETE']) {
    const result = await debug.fetch(request('/api/runs', {method, headers: {Cookie: cookie}}), env);
    assert.equal(result.status, 405);
    assert.equal((await result.json()).error, 'read_only');
  }
});

test('signed sessions reject tampering, malformed claims, expiry, excessive TTL, and cross-host replay', async () => {
  const env = environment();
  const time = now();
  const cookie = signedCookie(time, time + 300);
  const malformed = [
    cookie.replace(`.${time + 300}.`, `.${time + 600}.`),
    cookie.replace('=v1.', '=v2.'),
    signedCookie(time - 3601, time - 1), signedCookie(time + 60, time + 120),
    signedCookie(time, time + 3601), signedCookie(time, time),
    signedCookie(time, time + 300, 'https://other.example'),
    signedCookie(time, time + 300, ORIGIN, SECRET + 'wrong'),
    `${COOKIE}=v1.NaN.Infinity.signature`, `${COOKIE}=broken`,
    `${cookie}; ${cookie}`, `${COOKIE}=${'x'.repeat(5000)}`,
  ];
  for (const value of malformed) {
    const result = await debug.fetch(request('/api/catalog', {headers: {Cookie: value}}), env);
    assert.equal(result.status, 401, value.slice(0, 90));
  }
  const shortened = environment({DEBUG_ACCESS_EXPIRES_AT: String(time + 60)});
  assert.equal((await debug.fetch(request('/api/catalog', {headers: {Cookie: cookie}}), shortened)).status, 401);
  const anotherHost = new Request('https://another-debug.workers.dev/api/catalog', {headers: {Cookie: cookie}});
  assert.equal((await debug.fetch(anotherHost, env)).status, 403);
  assert.equal((await debug.fetch(new Request(ORIGIN.replace('https:', 'http:') + '/login'), env)).status, 403);
});

test('session lifetime stops at the global deadline and logout clears only this cookie', async () => {
  const env = environment({DEBUG_ACCESS_EXPIRES_AT: String(now() + 90)});
  const loggedIn = await debug.fetch(formRequest(), env);
  const setCookie = loggedIn.headers.get('Set-Cookie')!;
  const maxAge = Number(/Max-Age=(\d+)/.exec(setCookie)![1]);
  assert.ok(maxAge > 0 && maxAge <= 90);
  const claims = cookieValue(loggedIn).split('=')[1].split('.');
  assert.equal(claims[2], env.DEBUG_ACCESS_EXPIRES_AT);
  const expired = {...env, DEBUG_ACCESS_EXPIRES_AT: String(now() - 1)};
  assert.equal((await debug.fetch(request('/api/catalog', {headers: {Cookie: cookieValue(loggedIn)}}), expired)).status, 403);
  const logout = await debug.fetch(request('/logout', {method: 'POST', headers: {Origin: ORIGIN, Cookie: cookieValue(loggedIn)}}), env);
  assert.equal(logout.status, 303);
  assert.equal(logout.headers.get('Location'), '/login');
  assert.equal(logout.headers.get('Set-Cookie'), `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`);
  assertPrivate(logout);
  assert.equal((await debug.fetch(request('/logout'), env)).status, 405);
  assert.equal((await debug.fetch(request('/logout', {method: 'POST', headers: {Origin: 'https://attacker.example'}}), env)).status, 403);
});

test('only exact approved email identities redirect to the fixed primary Access entry', async () => {
  const env = environment();
  for (const email of ['researcher@mbzuai.ac.ae', 'RESEARCHER@MBZUAI.AC.AE', 'contact@amoriodi.xyz']) {
    const response = await debug.fetch(formRequest(email, {}, '/login?next=https://attacker.example'), env);
    assert.equal(response.status, 303);
    assert.equal(response.headers.get('Location'), PRIMARY_URL);
    assert.equal(response.headers.get('Set-Cookie'), null);
  }
  for (const email of ['name@mbzuai.ac.ae.attacker.example', 'name@sub.mbzuai.ac.ae', 'name@amoriodi.xyz', 'xcontact@amoriodi.xyz', 'name@@mbzuai.ac.ae', 'name@mbzuai.ac.ae\n@attacker.example']) {
    const response = await debug.fetch(formRequest(email), env);
    assert.equal(response.status, 401);
    assert.equal(response.headers.get('Location'), null);
    assert.equal(response.headers.get('Set-Cookie'), null);
  }
});

test('login rate limiting is keyed by connecting IP, returns 429, and fails closed if unavailable', async () => {
  const keys: string[] = [];
  const env = environment({DEBUG_LOGIN_RATE_LIMITER: {limit: async ({key}) => {keys.push(key); return {success: false};}}});
  const response = await debug.fetch(formRequest(CODE, {'CF-Connecting-IP': '192.0.2.8'}), env);
  assert.equal(response.status, 429);
  assert.equal(response.headers.get('Retry-After'), '60');
  assert.equal(response.headers.get('Set-Cookie'), null);
  assert.deepEqual(keys, ['login:192.0.2.8']);
  assertPrivate(response);
  const unavailable = environment({DEBUG_LOGIN_RATE_LIMITER: {limit: async () => {throw new Error('fixture outage');}}});
  const failed = await debug.fetch(formRequest(), unavailable);
  assert.equal(failed.status, 503);
  assert.equal(failed.headers.get('Set-Cookie'), null);
  assert.deepEqual(await failed.json(), {error: 'debug_access_unavailable'});
});
