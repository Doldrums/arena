import {json, route, type Env} from './router.ts';

// Temporary, separately deployed entrypoint. Production index.ts only accepts Access JWTs.
export interface DebugEnv extends Env {
  DEBUG_ACCESS_CODE_HASH?: string;
  DEBUG_SESSION_SECRET?: string;
  /** Absolute Unix timestamp in seconds; required on every request. */
  DEBUG_ACCESS_EXPIRES_AT?: string;
  DEBUG_LOGIN_RATE_LIMITER?: {limit(options: {key: string}): Promise<{success: boolean}>};
}

const COOKIE = '__Host-empira_debug';
const SESSION_SECONDS = 3600;
const BODY_LIMIT = 1024;
const PRIMARY_URL = 'https://research-arena.small-pine-3af7.workers.dev/';
const DEBUG_ORIGIN = 'https://research-arena-debug.small-pine-3af7.workers.dev';
const encoder = new TextEncoder();
type Config = {hash: Uint8Array<ArrayBuffer>; secret: string; expires: number};

function configuration(env: DebugEnv): Config | null {
  if (!env.DEBUG_ACCESS_CODE_HASH || !/^[a-f0-9]{64}$/.test(env.DEBUG_ACCESS_CODE_HASH)
      || !env.DEBUG_SESSION_SECRET || !/^[A-Za-z0-9_-]{43,256}$/.test(env.DEBUG_SESSION_SECRET)
      || env.DEBUG_SESSION_SECRET === env.DEBUG_ACCESS_CODE_HASH
      || !env.DEBUG_ACCESS_EXPIRES_AT || !/^[1-9][0-9]{9}$/.test(env.DEBUG_ACCESS_EXPIRES_AT)
      || typeof env.DEBUG_LOGIN_RATE_LIMITER?.limit !== 'function') return null;
  return {
    hash: Uint8Array.from(env.DEBUG_ACCESS_CODE_HASH.match(/../g)!, byte => parseInt(byte, 16)),
    secret: env.DEBUG_SESSION_SECRET,
    expires: Number(env.DEBUG_ACCESS_EXPIRES_AT),
  };
}

function privateResponse(response: Response, request: Request): Response {
  const result = new Response(request.method === 'HEAD' ? null : response.body, response);
  result.headers.set('Cache-Control', 'private, no-store, max-age=0');
  result.headers.set('CDN-Cache-Control', 'no-store');
  result.headers.set('Cloudflare-CDN-Cache-Control', 'no-store');
  result.headers.set('Pragma', 'no-cache');
  result.headers.set('Referrer-Policy', 'same-origin');
  result.headers.set('X-Content-Type-Options', 'nosniff');
  result.headers.set('X-Frame-Options', 'DENY');
  result.headers.delete('ETag');
  result.headers.delete('Last-Modified');
  return result;
}

function redirect(location: '/' | '/login' | typeof PRIMARY_URL): Response {
  return new Response(null, {status: 303, headers: {Location: location}});
}

function login(message = '', status = 200): Response {
  return new Response(`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Sign in · Empira</title>
<style>
:root{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;color:#242424;background:#f4f3f1;color-scheme:light}
*{box-sizing:border-box}body{margin:0;min-height:100svh;display:grid;place-items:center;padding:24px}
main{width:100%;max-width:420px;background:#fff;border:1px solid #e7e5e2;border-radius:24px;padding:40px;box-shadow:0 12px 50px #24242408}
.brand{font-size:19px;font-weight:650;letter-spacing:-.7px;margin:0 0 38px}h1{font-size:26px;line-height:1.2;font-weight:600;letter-spacing:-.9px;margin:0 0 12px}
p{color:#72716f;font-size:14px;line-height:1.6;margin:0 0 28px}label{display:block;font-size:13px;font-weight:550;margin-bottom:9px}
input,button{width:100%;font:inherit;border-radius:10px;padding:13px 14px}input{font-size:15px;border:1px solid #d6d4d0;background:#fff;color:#242424}
input:focus-visible,button:focus-visible{outline:2px solid #656565;outline-offset:3px}button{margin-top:16px;border:0;background:#292929;color:#fff;font-size:14px;font-weight:550;cursor:pointer}
button:hover{background:#414141}.note{font-size:12px;margin:24px 0 0}.message{color:#3e3d3b;margin:16px 0 0;font-size:13px}
@media(max-width:460px){main{padding:30px 24px}}
</style></head><body><main><div class="brand">Empira</div><h1>Welcome back</h1>
<p>Enter your work email or temporary access code to continue.</p>
<form method="post" action="/login"><label for="credential">Email or access code</label>
<input id="credential" name="credential" type="text" placeholder="you@mbzuai.ac.ae" autocomplete="off" autocapitalize="none" spellcheck="false" maxlength="256" required autofocus>
<button type="submit">Continue</button></form>
${message ? `<p class="message" role="alert">${message}</p>` : ''}
<p class="note">Work email continues to secure organization sign-in. Temporary access expires automatically.</p>
</main></body></html>`, {status, headers: {
    'Content-Type': 'text/html; charset=utf-8',
    'Content-Security-Policy': `default-src 'none'; style-src 'unsafe-inline'; form-action 'self' ${PRIMARY_URL} https://empira-research.cloudflareaccess.com; base-uri 'none'; frame-ancestors 'none'`,
  }});
}

async function credentialFrom(request: Request): Promise<string | null> {
  if (request.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase() !== 'application/x-www-form-urlencoded') return null;
  const length = request.headers.get('Content-Length');
  if (length && (!/^[0-9]+$/.test(length) || Number(length) > BODY_LIMIT)) return null;
  if (!request.body) return null;
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > BODY_LIMIT) { await reader.cancel(); return null; }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    const form = new URLSearchParams(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
    const values = form.getAll('credential');
    if (values.length !== 1 || values[0].length > 256) return null;
    return values[0].trim();
  } catch {
    return null;
  } finally {
    reader.releaseLock();
  }
}

function base64url(bytes: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function hmacKey(config: Config): Promise<CryptoKey> {
  return crypto.subtle.importKey('raw', encoder.encode(config.secret), {name: 'HMAC', hash: 'SHA-256'}, false, ['sign', 'verify']);
}

function signedData(origin: string, claims: string): Uint8Array<ArrayBuffer> {
  return encoder.encode(`empira-debug:${origin}:${claims}`);
}

async function sessionCookie(config: Config, origin: string, now: number): Promise<string> {
  const exp = Math.min(now + SESSION_SECONDS, config.expires);
  const claims = `v1.${now}.${exp}`;
  const signature = base64url(await crypto.subtle.sign('HMAC', await hmacKey(config), signedData(origin, claims)));
  return `${COOKIE}=${claims}.${signature}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${exp - now}`;
}

async function authenticated(request: Request, config: Config, now: number): Promise<number | null> {
  const header = request.headers.get('Cookie') ?? '';
  if (header.length > 4096) return null;
  const cookies = header.split(';').map(value => value.trim()).filter(value => value.startsWith(`${COOKIE}=`));
  if (cookies.length !== 1) return null;
  const token = cookies[0].slice(COOKIE.length + 1);
  const match = /^v1\.([1-9][0-9]{9})\.([1-9][0-9]{9})\.([A-Za-z0-9_-]{43})$/.exec(token);
  if (!match) return null;
  const iat = Number(match[1]), exp = Number(match[2]);
  if (iat > now || exp <= now || exp <= iat || exp > config.expires || exp - iat > SESSION_SECONDS) return null;
  const signature = Uint8Array.from(atob(match[3].replace(/-/g, '+').replace(/_/g, '/') + '='), char => char.charCodeAt(0));
  if (base64url(signature.buffer) !== match[3]) return null;
  const valid = await crypto.subtle.verify('HMAC', await hmacKey(config), signature,
    signedData(new URL(request.url).origin, `v1.${iat}.${exp}`));
  return valid ? exp : null;
}

function sameOrigin(request: Request): boolean {
  return request.headers.get('Origin') === new URL(request.url).origin
    && request.headers.get('Sec-Fetch-Site') !== 'cross-site';
}

async function handle(request: Request, env: DebugEnv): Promise<Response> {
  const url = new URL(request.url);
  if (url.origin !== DEBUG_ORIGIN) return json({error: 'invalid_debug_host'}, 403);
  const config = configuration(env);
  if (!config) return json({error: 'debug_access_not_configured'}, 503);
  const now = Math.floor(Date.now() / 1000);
  if (now >= config.expires) return json({error: 'debug_access_expired'}, 403);
  if (url.pathname === '/logout') {
    if (request.method !== 'POST') return json({error: 'method_not_allowed'}, 405);
    if (!sameOrigin(request)) return json({error: 'invalid_origin'}, 403);
    const response = redirect('/login');
    response.headers.set('Set-Cookie', `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`);
    return response;
  }
  if (url.pathname === '/login') {
    if (request.method === 'GET' || request.method === 'HEAD') {
      return await authenticated(request, config, now) ? redirect('/') : login();
    }
    if (request.method !== 'POST') return json({error: 'method_not_allowed'}, 405);
    if (!sameOrigin(request)) return json({error: 'invalid_origin'}, 403);
    const ip = request.headers.get('CF-Connecting-IP') ?? '';
    const key = `login:${/^[0-9a-fA-F:.]{3,64}$/.test(ip) ? ip : 'unknown'}`;
    let allowed: boolean;
    try { allowed = (await env.DEBUG_LOGIN_RATE_LIMITER!.limit({key})).success === true; }
    catch { return json({error: 'debug_access_unavailable'}, 503); }
    if (!allowed) {
      const response = login('Too many attempts. Please try again in a minute.', 429);
      response.headers.set('Retry-After', '60');
      return response;
    }
    const credential = await credentialFrom(request);
    if (!credential) return login('Enter a valid work email or access code.', 400);
    const email = credential.toLowerCase();
    if (email === 'contact@amoriodi.xyz' || /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@mbzuai\.ac\.ae$/.test(email)) return redirect(PRIMARY_URL);
    const digest = await crypto.subtle.digest('SHA-256', encoder.encode(credential));
    // Workers' native constant-time comparison always receives two 32-byte SHA-256 digests.
    const subtle = crypto.subtle as SubtleCrypto & {timingSafeEqual(a: ArrayBuffer, b: ArrayBuffer): boolean};
    if (!subtle.timingSafeEqual(digest, config.hash.buffer)) return login('Enter a valid work email or access code.', 401);
    // Re-read time after body/cryptographic work so a login cannot cross the global deadline.
    const issued = Math.floor(Date.now() / 1000);
    if (issued >= config.expires) return json({error: 'debug_access_expired'}, 403);
    const response = redirect('/');
    response.headers.set('Set-Cookie', await sessionCookie(config, url.origin, issued));
    return response;
  }
  const sessionExpires = await authenticated(request, config, now);
  if (!sessionExpires) {
    if (url.pathname === '/api' || url.pathname.startsWith('/api/') || !['GET', 'HEAD'].includes(request.method)) {
      return json({error: 'authentication_required'}, 401);
    }
    return redirect('/login');
  }
  if (Math.floor(Date.now() / 1000) >= config.expires) return json({error: 'debug_access_expired'}, 403);
  return route(request, env, {sessionExpiresAt: Math.min(sessionExpires, config.expires) * 1000});
}

export default {
  async fetch(request: Request, env: DebugEnv): Promise<Response> {
    return privateResponse(await handle(request, env), request);
  },
};
