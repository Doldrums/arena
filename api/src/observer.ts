/** Private VPC service only. This module never uses the public-network fetch API. */
export interface ObserverBinding {
  fetch(request: Request): Promise<Response>;
}
export interface ObserverOptions {
  /** Verified authentication expiry, in milliseconds; never derived from a request header. */
  sessionExpiresAt?: number;
}

const ORIGIN = 'http://127.0.0.1:8080';
const MAX_RESPONSE_MS = 30_000;
const HEADER_TIMEOUT_MS = 10_000;
const RUN_ID = /^[a-f0-9]{20}$/;
const DETAIL_KINDS = new Set(['program', 'method', 'proposal', 'research-tools',
  'research-tool-artifacts', 'research-cells', 'research-tool-jobs']);
const PAGE_QUERIES: Record<string, Set<string>> = {
  packings: new Set(['offset', 'limit', 'sort', 'island', 'q']),
  workflow: new Set(['limit', 'before', 'actor', 'q']),
  'llm-calls': new Set(['offset', 'limit', 'q']),
};
const PRIVATE_HEADERS = {
  'Cache-Control': 'private, no-store',
  'CDN-Cache-Control': 'no-store',
  'Cloudflare-CDN-Cache-Control': 'no-store',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
  'X-Frame-Options': 'DENY',
};

function failure(error: string, status: number): Response {
  return Response.json({error}, {status, headers: PRIVATE_HEADERS});
}

export function observerConfigured(binding?: ObserverBinding): binding is ObserverBinding {
  return typeof binding?.fetch === 'function';
}

/** Rebuild a canonical path, never interpret a client-supplied value as an origin. */
function targetFor(url: URL): {url: URL; stream: boolean} | null {
  if (url.pathname.length > 2048 || url.search.length > 4096) return null;
  const encoded = url.pathname.split('/').slice(1);
  let parts: string[];
  try { parts = encoded.map(part => decodeURIComponent(part)); } catch { return null; }
  // Encoded slashes, controls, percent escapes and dot segments cannot become a second path.
  if (parts.some(part => !part || /[\\/\x00-\x1f\x7f%]/.test(part) || part === '.' || part === '..')) return null;
  let query = new Set<string>();
  let stream = false;
  if (parts.length === 2 && parts[0] === 'api' && parts[1] === 'stream') {
    stream = true;
    query = new Set(['run']);
    if (!RUN_ID.test(url.searchParams.get('run') || '')) return null;
  } else if (parts[0] !== 'api' || parts[1] !== 'runs') return null;
  else if (parts.length === 2) { /* list */ }
  else if (!RUN_ID.test(parts[2])) return null;
  else if (parts.length === 3) { /* snapshot */ }
  else if (parts.length === 4 && Object.hasOwn(PAGE_QUERIES, parts[3])) query = PAGE_QUERIES[parts[3]];
  else if (!(parts.length === 5 && (DETAIL_KINDS.has(parts[3]) || parts[3] === 'workflow' || parts[3] === 'llm-calls'))) return null;
  const seen = new Set<string>();
  for (const [key, value] of url.searchParams) {
    if (!query.has(key) || seen.has(key) || value.length > 1024 || /[\x00-\x1f\x7f]/.test(value)) return null;
    if ((key === 'offset' || key === 'limit') && !/^\d{1,9}$/.test(value)) return null;
    seen.add(key);
  }
  const target = new URL(ORIGIN);
  target.pathname = '/' + parts.map(part => encodeURIComponent(part)).join('/');
  target.search = url.searchParams.toString();
  return {url: target, stream};
}

function discard(response: Response): void {
  void response.body?.cancel().catch(() => {});
}

export async function proxyObserver(request: Request, binding: ObserverBinding | undefined,
  options: ObserverOptions = {}): Promise<Response> {
  if (request.method !== 'GET' && request.method !== 'HEAD') return failure('read_only', 405);
  const target = targetFor(new URL(request.url));
  if (!target) return failure('not_found', 404);
  if (!observerConfigured(binding)) return failure('observer_not_connected', 503);
  const now = Date.now();
  const sessionExpiry = options.sessionExpiresAt;
  if (sessionExpiry !== undefined && (!Number.isFinite(sessionExpiry) || sessionExpiry <= now)) {
    return failure('observer_session_expired', 503);
  }
  const deadline = Math.min(now + MAX_RESPONSE_MS, sessionExpiry ?? Infinity);
  const abort = new AbortController();
  let headerTimer: ReturnType<typeof setTimeout> | undefined;
  let responseTimer: ReturnType<typeof setTimeout> | undefined;
  let stopBody: (() => void) | undefined;
  const disconnected = () => { abort.abort(); stopBody?.(); };
  const cleanup = () => {
    clearTimeout(headerTimer);
    clearTimeout(responseTimer);
    request.signal.removeEventListener('abort', disconnected);
  };
  request.signal.addEventListener('abort', disconnected, {once: true});
  if (request.signal.aborted) { cleanup(); return failure('observer_unavailable', 503); }
  let upstream: Response;
  try {
    const source = new Request(target.url, {
      method: 'GET', redirect: 'manual', signal: abort.signal,
      // Deliberately omit all incoming credentials, headers and request bodies.
      headers: {Accept: target.stream ? 'text/event-stream' : 'application/json'},
    });
    const pending = binding.fetch(source).then(response => {
      if (abort.signal.aborted) { discard(response); throw new Error('observer_aborted'); }
      return response;
    });
    upstream = await Promise.race([pending, new Promise<never>((_, reject) => {
      headerTimer = setTimeout(() => { abort.abort(); reject(new Error('observer_timeout')); },
        Math.min(HEADER_TIMEOUT_MS, Math.max(0, deadline - Date.now())));
    })]);
    clearTimeout(headerTimer);
  } catch {
    abort.abort(); cleanup();
    return failure('observer_unavailable', 503);
  }
  const contentType = upstream.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase();
  const expectedType = target.stream ? 'text/event-stream' : 'application/json';
  if (Date.now() >= deadline || request.signal.aborted) {
    abort.abort(); discard(upstream); cleanup();
    return failure('observer_session_expired', 503);
  }
  if (upstream.status !== 200 || contentType !== expectedType || !upstream.body) {
    abort.abort(); discard(upstream); cleanup();
    if (upstream.status === 404) return failure('observer_record_not_found', 404);
    if (upstream.status === 400) return failure('invalid_observer_request', 400);
    if (upstream.status === 503) return failure('observer_unavailable', 503);
    return failure('observer_bad_response', 502);
  }
  const headers = {...PRIVATE_HEADERS, 'Content-Type': expectedType + '; charset=utf-8'};
  if (request.method === 'HEAD') {
    abort.abort(); discard(upstream); cleanup();
    return new Response(null, {headers});
  }
  const reader = upstream.body.getReader();
  let finished = false;
  let downstream: ReadableStreamDefaultController<Uint8Array>;
  const finish = (close: boolean) => {
    if (finished) return;
    finished = true;
    cleanup();
    abort.abort();
    void reader.cancel().catch(() => {});
    if (close) downstream.close();
  };
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      downstream = controller;
      stopBody = () => finish(true);
      responseTimer = setTimeout(stopBody, Math.max(0, deadline - Date.now()));
    },
    async pull(controller) {
      if (finished) return;
      try {
        const {done, value} = await reader.read();
        if (finished) return;
        if (done) { finish(true); return; }
        controller.enqueue(value);
      } catch {
        if (finished) return;
        finish(false);
        controller.error(new Error('Observer connection interrupted.'));
      }
    },
    cancel() { finish(false); },
  });
  return new Response(body, {headers});
}
