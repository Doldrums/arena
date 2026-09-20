import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createLocalJWKSet, exportJWK, generateKeyPair, SignJWT} from 'jose';
import worker from '../../api/src/index.ts';
import dev from '../../api/src/dev.ts';
import {route, type Env} from '../../api/src/router.ts';
import {verifyAccessToken} from '../../api/src/auth.ts';

const env: Env = {ASSETS: {fetch: async request => new Response(new URL(request.url).pathname)}};
const request = (path: string, init?: RequestInit) => new Request(`http://localhost${path}`, init);

test('production protects HTML, assets and API even when Access is unconfigured', async () => {
  for (const path of ['/', '/style.css', '/api/catalog', '/api/insights', '/api/references', '/experiments']) {
    const response = await worker.fetch(request(path), env);
    assert.equal(response.status, 503);
    assert.equal((await response.json()).error, 'access_not_configured');
  }
});
test('production rejects missing and forged tokens; local adapter rejects remote host', async () => {
  const protectedEnv = {...env, ACCESS_TEAM_DOMAIN: 'https://arena.cloudflareaccess.com', ACCESS_AUD: 'our-team-app'};
  assert.equal((await worker.fetch(request('/'), protectedEnv)).status, 401);
  assert.equal((await worker.fetch(request('/', {headers: {'Cf-Access-Jwt-Assertion': 'forged'}}), protectedEnv)).status, 403);
  assert.equal((await dev.fetch(new Request('https://arena.example.com/'), env)).status, 403);
});
test('Access verifies signature, issuer, audience and expiration', async () => {
  const {privateKey, publicKey} = await generateKeyPair('RS256');
  const keys = createLocalJWKSet({keys: [{...await exportJWK(publicKey), kid: 'fixture'}]});
  const config = {ACCESS_TEAM_DOMAIN: 'https://arena.cloudflareaccess.com', ACCESS_AUD: 'arena-app'};
  const sign = (aud = 'arena-app', issuer = config.ACCESS_TEAM_DOMAIN, expiry = '5m') => new SignJWT({})
    .setProtectedHeader({alg: 'RS256', kid: 'fixture'}).setSubject('team-user')
    .setIssuedAt().setIssuer(issuer).setAudience(aud).setExpirationTime(expiry).sign(privateKey);
  assert.equal((await verifyAccessToken(await sign(), config, keys)).sub, 'team-user');
  await assert.rejects(verifyAccessToken(await sign('another-app'), config, keys));
  await assert.rejects(verifyAccessToken(await sign('arena-app', 'https://attacker.example'), config, keys));
  await assert.rejects(verifyAccessToken(await sign('arena-app', config.ACCESS_TEAM_DOMAIN, '-1m'), config, keys));
  const wrong = await generateKeyPair('RS256');
  const otherKeys = createLocalJWKSet({keys: [{...await exportJWK(wrong.publicKey), kid: 'fixture'}]});
  await assert.rejects(verifyAccessToken(await sign(), config, otherKeys));
});
test('catalog and participants are real registry snapshots, with no fake launch support', async () => {
  const catalog = await (await route(request('/api/catalog'), env)).json();
  assert.equal(catalog.tasks.length, 1138);
  const participants = await (await route(request('/api/participants'), env)).json();
  assert.equal(participants.participants.length, 3);
  assert.equal((await route(request('/api/runs'), env)).status, 503);
  assert.equal((await route(request('/api/runs', {method: 'POST'}), env)).status, 405);
  assert.equal((await route(request('/api/unknown'), env)).status, 404);
});
test('asset routing preserves the native experiment view and HEAD semantics', async () => {
  const response = await route(request('/experiments?run=abc'), env);
  assert.equal(await response.text(), '/experiment.html');
  assert.equal(response.headers.get('Cache-Control'), 'private, no-store');
  assert.equal(await (await route(request('/'), env)).text(), '/index.html');
  assert.equal(await (await route(request('/api/catalog', {method: 'HEAD'}), env)).text(), '');
});

test('scientific overview counts every catalog task once and serves evidence separately', async () => {
  const catalog = await (await route(request('/api/catalog'), env)).json();
  const insights = await (await route(request('/api/insights'), env)).json();
  const references = await (await route(request('/api/references'), env)).json();
  assert.equal(insights.schema, 'arena.insights/1');
  assert.equal(references.schema, 'arena.references/1');
  assert.deepEqual(Object.keys(insights.task_annotations).sort(), catalog.tasks.map((t: {id: string}) => t.id).sort());
  for (const groups of [insights.domains, insights.task_types]) {
    assert.equal(groups.reduce((sum: number, item: {total: number}) => sum + item.total, 0), catalog.tasks.length);
    assert.ok(Math.abs(groups.reduce((sum: number, item: {percentage: number}) => sum + item.percentage, 0) - 100) < 1e-8);
  }
  assert.equal(await (await route(request('/api/insights', {method: 'HEAD'}), env)).text(), '');
});
