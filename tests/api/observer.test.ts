import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';
import {route, type Env} from '../../api/src/router.ts';
import worker from '../../api/src/index.ts';
import {proxyObserver, type ObserverBinding} from '../../api/src/observer.ts';

const RUN = '0123456789abcdef0123';
const PREFIX = '/api/runs/' + RUN;
const req = (path: string, init?: RequestInit) => new Request('https://arena.example' + path, init);
const env = (fetch?: ObserverBinding['fetch']): Env => ({
  ASSETS: {fetch: async () => new Response('asset')},
  ...(fetch ? {OBSERVER: {fetch}} : {}),
});
const ok = () => Response.json({runs: [], fixture: true});
function privateHeaders(response: Response) {
  assert.equal(response.headers.get('Cache-Control'), 'private, no-store');
  assert.equal(response.headers.get('CDN-Cache-Control'), 'no-store');
  assert.equal(response.headers.get('Cloudflare-CDN-Cache-Control'), 'no-store');
  assert.equal(response.headers.get('X-Content-Type-Options'), 'nosniff');
}

function openSource() {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  let cancelled = 0;
  const stream = new ReadableStream<Uint8Array>({
    start(value) { controller = value; },
    cancel() { cancelled++; },
  });
  return {response: new Response(stream, {headers: {'Content-Type': 'text/event-stream'}}),
    send: (text: string) => controller.enqueue(new TextEncoder().encode(text)),
    close: () => controller.close(), cancelled: () => cancelled};
}

test('private observer fails closed without a VPC binding and leaves control inaccessible', async () => {
  for (const path of ['/api/runs', PREFIX, '/api/stream?run=' + RUN]) {
    const response = await route(req(path), env());
    assert.equal(response.status, 503);
    assert.equal((await response.json()).error, 'observer_not_connected');
    privateHeaders(response);
  }
  let called = 0;
  const configured = env(async () => { called++; return ok(); });
  for (const path of ['/api/control/results', '/api/queue', '/api/control/reload', '/api/runs/unknown']) {
    assert.equal((await route(req(path), configured)).status, 404);
  }
  for (const method of ['POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']) {
    assert.equal((await route(req('/api/runs', {method}), configured)).status, 405);
  }
  assert.equal(called, 0);
});

test('observer capabilities describe configured read-only routing without claiming a live health probe', async () => {
  for (const configured of [false, true]) {
    const response = await route(req('/api/health'), configured ? env(async () => { throw new Error('must not probe'); }) : env());
    const value = await response.json();
    assert.equal(value.observer_configured, configured);
    assert.equal(value.capabilities.native_runs, configured);
    assert.equal(value.capabilities.run_observation, configured);
    assert.equal(value.capabilities.launch, false);
  }
});

test('production authentication still precedes the private observer binding', async () => {
  let calls = 0;
  const configured = {...env(async () => { calls++; return ok(); }),
    ACCESS_TEAM_DOMAIN: 'https://arena.cloudflareaccess.com', ACCESS_AUD: 'our-team-app'};
  assert.equal((await worker.fetch(req('/api/runs'), configured)).status, 401);
  assert.equal((await worker.fetch(req('/api/stream?run=' + RUN, {headers: {'Cf-Access-Jwt-Assertion': 'forged'}}), configured)).status, 403);
  assert.equal(calls, 0);
});

test('observer forwards only exact native read routes and known query keys', async () => {
  const paths = ['/api/runs', PREFIX, ...['program', 'method', 'proposal', 'research-tools',
    'research-tool-artifacts', 'research-cells', 'research-tool-jobs', 'workflow', 'llm-calls']
    .map(kind => `${PREFIX}/${kind}/fixture%3A1`),
    `${PREFIX}/packings?offset=0&limit=120&sort=score&island=all&q=circle+packing`,
    `${PREFIX}/workflow?limit=60&before=fixture%3A1&actor=all&q=example`,
    `${PREFIX}/llm-calls?offset=0&limit=50&q=example`];
  for (const path of paths) {
    let requested: Request | undefined;
    const response = await route(req(path), env(async request => { requested = request; return ok(); }));
    assert.equal(response.status, 200, path);
    assert.deepEqual(await response.json(), {runs: [], fixture: true});
    assert.equal(new URL(requested!.url).origin, 'http://127.0.0.1:8080');
    assert.equal(new URL(requested!.url).pathname + new URL(requested!.url).search, path);
  }
});

test('observer rejects unknown paths, ambiguous identifiers and query expansion before making a request', async () => {
  let calls = 0;
  const configured = env(async () => { calls++; return ok(); });
  const paths = ['/api/runs/', '/api/runs//', PREFIX + '/', PREFIX + '/unknown',
    PREFIX + '/program', PREFIX + '/program/a/more', PREFIX + '/packings/item',
    PREFIX + '/program/%2Fapi%2Fcontrol', PREFIX + '/program/%5Csecret',
    PREFIX + '/program/%252e%252e', PREFIX + '/program/%00', PREFIX + '/program/%zz',
    '/api/runs?target=http://attacker.example', '/api/runs?run=' + RUN,
    PREFIX + '?x=1', PREFIX + '/workflow?limit=1&limit=2',
    PREFIX + '/workflow?limit=-1', PREFIX + '/llm-calls?offset=Infinity',
    PREFIX + '/workflow?q=%00', PREFIX + '/packings?q=' + 'x'.repeat(1025),
    '/api/stream', '/api/stream?run=unknown', '/api/stream?run=' + RUN + '&run=' + RUN,
    '/api/stream?run=' + RUN + '&url=http://attacker.example'];
  for (const path of paths) assert.equal((await route(req(path), configured)).status, 404, path);
  assert.equal(calls, 0);
});

test('VPC requests omit browser credentials, forwarding headers and redirect following', async () => {
  let requested!: Request;
  const response = await route(req(PREFIX + '/workflow?q=hello', {headers: {
    Authorization: 'Bearer browser-secret', Cookie: 'session=browser-secret',
    'Cf-Access-Jwt-Assertion': 'browser-secret', 'CF-Access-Client-Secret': 'browser-secret',
    'X-Forwarded-Host': 'attacker.example', Range: 'bytes=0-10',
    'Last-Event-ID': 'untrusted', Accept: 'text/html',
  }}), env(async value => {
    requested = value;
    return Response.json({fixture: true}, {headers: {
      'Set-Cookie': 'origin-secret', Location: 'https://attacker.example',
      ETag: 'private-tag', 'Cache-Control': 'public, max-age=86400',
      'Access-Control-Allow-Origin': '*', 'X-Private-Config': 'private-value',
    }});
  }));
  assert.equal(requested.redirect, 'manual');
  assert.equal(requested.method, 'GET');
  assert.deepEqual([...requested.headers], [['accept', 'application/json']]);
  assert.equal(requested.body, null);
  for (const name of ['Set-Cookie', 'Location', 'ETag', 'Access-Control-Allow-Origin', 'X-Private-Config']) {
    assert.equal(response.headers.get(name), null);
  }
  privateHeaders(response);
  assert.deepEqual(await response.json(), {fixture: true});
});

test('upstream redirects, wrong content and errors reveal no private origin response', async () => {
  for (const [status, contentType, expected] of [[302, 'text/html', 502], [200, 'text/html', 502],
    [401, 'application/json', 502], [500, 'application/json', 502],
    [404, 'application/json', 404], [400, 'application/json', 400], [503, 'application/json', 503]] as const) {
    let cancelled = 0;
    const body = new ReadableStream({cancel() { cancelled++; }});
    const response = await route(req('/api/runs'), env(async () => new Response(body, {
      status, headers: {'Content-Type': contentType, Location: 'http://private-origin/path'},
    })));
    assert.equal(response.status, expected);
    assert.equal(response.headers.get('Location'), null);
    assert.equal(cancelled, 1);
    privateHeaders(response);
    assert.equal((await response.text()).includes('private-origin'), false);
  }
  const failed = await route(req('/api/runs'), env(async () => { throw new Error('/private/config secret'); }));
  assert.equal(failed.status, 503);
  assert.deepEqual(await failed.json(), {error: 'observer_unavailable'});
});

test('HEAD uses upstream GET, cancels its body, and returns only sanitized headers', async () => {
  let cancelled = 0;
  let request!: Request;
  const body = new ReadableStream({cancel() { cancelled++; }});
  const response = await route(req('/api/runs', {method: 'HEAD'}), env(async value => {
    request = value;
    return new Response(body, {headers: {'Content-Type': 'application/json'}});
  }));
  assert.equal(request.method, 'GET');
  assert.equal(request.signal.aborted, true);
  assert.equal(cancelled, 1);
  assert.equal(await response.text(), '');
  assert.equal(response.status, 200);
  privateHeaders(response);
});

test('SSE is streamed without buffering; consumer cancellation closes and aborts origin', async () => {
  const source = openSource();
  let request!: Request;
  const response = await route(req('/api/stream?run=' + RUN), env(async value => { request = value; return source.response; }));
  assert.equal(response.status, 200);
  assert.equal(request.headers.get('Accept'), 'text/event-stream');
  assert.equal(response.headers.get('Content-Type'), 'text/event-stream; charset=utf-8');
  privateHeaders(response);
  const reader = response.body!.getReader();
  source.send('event: snapshot\ndata: {}\n\n');
  assert.equal(new TextDecoder().decode((await reader.read()).value), 'event: snapshot\ndata: {}\n\n');
  source.send(': heartbeat\n\n');
  assert.equal(new TextDecoder().decode((await reader.read()).value), ': heartbeat\n\n');
  await reader.cancel();
  assert.equal(source.cancelled(), 1);
  assert.equal(request.signal.aborted, true);
});

test('SSE client disconnect and normal upstream completion both release origin resources', async () => {
  for (const disconnect of [true, false]) {
    const source = openSource();
    const client = new AbortController();
    let origin!: Request;
    const response = await route(req('/api/stream?run=' + RUN, {signal: client.signal}), env(async request => { origin = request; return source.response; }));
    const reader = response.body!.getReader();
    if (disconnect) client.abort(); else source.close();
    assert.equal((await reader.read()).done, true);
    assert.equal(origin.signal.aborted, true);
    assert.equal(source.cancelled(), disconnect ? 1 : 0);
  }
});

test('SSE closes by verified session expiry and reconnects must authenticate again', async () => {
  const source = openSource();
  let origin!: Request;
  const response = await route(req('/api/stream?run=' + RUN), env(async request => { origin = request; return source.response; }),
    {sessionExpiresAt: Date.now() + 60});
  const result = await Promise.race([response.body!.getReader().read(), delay(300).then(() => ({timedOut: true}))]);
  assert.deepEqual(result, {value: undefined, done: true});
  assert.equal(source.cancelled(), 1);
  assert.equal(origin.signal.aborted, true);
  let requests = 0;
  for (const expiry of [Date.now() - 1, NaN, Infinity]) {
    const expired = await route(req('/api/runs'), env(async () => { requests++; return ok(); }), {sessionExpiresAt: expiry});
    assert.equal(expired.status, 503);
    assert.equal((await expired.json()).error, 'observer_session_expired');
  }
  assert.equal(requests, 0);
});

test('SSE has a 30-second upper bound even with a longer verified session', async t => {
  t.mock.timers.enable({apis: ['setTimeout', 'Date']});
  const source = openSource();
  let origin!: Request;
  const response = await route(req('/api/stream?run=' + RUN), env(async request => { origin = request; return source.response; }),
    {sessionExpiresAt: Date.now() + 3600_000});
  const pending = response.body!.getReader().read();
  t.mock.timers.tick(30_000);
  assert.equal((await pending).done, true);
  assert.equal(source.cancelled(), 1);
  assert.equal(origin.signal.aborted, true);
});

test('header retrieval has a timeout and late upstream bodies are cancelled', async t => {
  t.mock.timers.enable({apis: ['setTimeout', 'Date']});
  let resolve!: (response: Response) => void;
  let request!: Request;
  const pending = route(req('/api/runs'), env(async value => {
    request = value;
    return new Promise<Response>(done => { resolve = done; });
  }));
  t.mock.timers.tick(10_000);
  const response = await pending;
  assert.equal(response.status, 503);
  assert.equal(request.signal.aborted, true);
  let cancelled = false;
  resolve(new Response(new ReadableStream({cancel() { cancelled = true; }}), {headers: {'Content-Type': 'application/json'}}));
  await Promise.resolve(); await Promise.resolve();
  assert.equal(cancelled, true);
});

test('expired header wait and an already disconnected client never leave a live origin request', async () => {
  let origin!: Request;
  const response = await route(req('/api/runs'), env(async request => {
    origin = request;
    return new Promise<Response>(() => {});
  }), {sessionExpiresAt: Date.now() + 25});
  assert.equal(response.status, 503);
  assert.equal(origin.signal.aborted, true);
  const abort = new AbortController(); abort.abort();
  let called = false;
  assert.equal((await proxyObserver(req('/api/runs', {signal: abort.signal}), {fetch: async () => { called = true; return ok(); }})).status, 503);
  assert.equal(called, false);
});
