import catalog from '../../registry/catalog.json';
import participants from '../../registry/participants.json';
import insights from '../../registry/insights.json';
import references from '../../registry/references.json';
import searchFamilies from '../../registry/search-families.json';
import resultsOverview from '../../registry/results-overview.json';
import type {AccessConfig} from './auth.ts';
import {observerConfigured, proxyObserver, type ObserverBinding, type ObserverOptions} from './observer.ts';

export interface Env extends AccessConfig {
  ASSETS: {fetch(request: Request): Promise<Response>};
  OBSERVER?: ObserverBinding;
}

export function json(value: unknown, status = 200): Response {
  return Response.json(value, {status, headers: {
    'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff',
  }});
}

export async function route(request: Request, env: Env, options: ObserverOptions = {}): Promise<Response> {
  const url = new URL(request.url);
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return json({error: 'read_only', message: 'This milestone does not submit or launch experiments.'}, 405);
  }
  let response: Response;
  if (url.pathname === '/api/health') {
    const connected = observerConfigured(env.OBSERVER);
    response = json({status: 'ok', component: 'arena', version: '0.1.0', mode: connected ? 'read_only' : 'catalog_only',
      observer_configured: connected,
      capabilities: {catalog: true, participants: true, insights: true, references: true, search_families: true, native_runs: connected, run_observation: connected, launch: false}});
  } else if (url.pathname === '/api/catalog') {
    response = json(catalog);
  } else if (url.pathname === '/api/participants') {
    response = json(participants);
  } else if (url.pathname === '/api/insights') {
    response = json(insights);
  } else if (url.pathname === '/api/references') {
    response = json(references);
  } else if (url.pathname === '/api/search-families') {
    response = json(searchFamilies);
  } else if (url.pathname === '/api/results-overview') {
    // Explicitly published measurements only; never proxy the private control API.
    response = json(resultsOverview);
  } else if (url.pathname === '/api/runs' || url.pathname.startsWith('/api/runs/') || url.pathname === '/api/stream') {
    response = await proxyObserver(request, env.OBSERVER, options);
  } else if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
    response = json({error: 'not_found'}, 404);
  } else {
    if (url.pathname === '/') url.pathname = '/index.html';
    if (url.pathname === '/experiments' || url.pathname === '/experiments/') url.pathname = '/experiment.html';
    if (url.pathname === '/results' || url.pathname === '/results/') url.pathname = '/results.html';
    if (url.pathname === '/experiments/results' || url.pathname === '/experiments/results/') url.pathname = '/experiment-results.html';
    if (['/experiments/queue', '/experiments/queue/', '/queue', '/queue/'].includes(url.pathname)) url.pathname = '/queue.html';
    response = await env.ASSETS.fetch(new Request(url, request));
    response = new Response(response.body, response);
    response.headers.set('Cache-Control', 'private, no-store');
    response.headers.set('X-Content-Type-Options', 'nosniff');
    response.headers.set('Referrer-Policy', 'no-referrer');
    response.headers.set('X-Frame-Options', 'DENY');
  }
  return request.method === 'HEAD' ? new Response(null, response) : response;
}
