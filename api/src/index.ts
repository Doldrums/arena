import {accessIssuer, verifyAccessToken} from './auth.ts';
import {json, route, type Env} from './router.ts';

// Worker runs BEFORE all static assets: registry metadata and HTML share the same gate.
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (!accessIssuer(env)) return json({error: 'access_not_configured'}, 503);
    const token = request.headers.get('Cf-Access-Jwt-Assertion');
    if (!token) return json({error: 'authentication_required'}, 401);
    let sessionExpiresAt: number;
    try {
      const identity = await verifyAccessToken(token, env);
      sessionExpiresAt = identity.exp! * 1000;
    } catch {
      return json({error: 'invalid_access_token'}, 403);
    }
    return route(request, env, {sessionExpiresAt});
  },
};
