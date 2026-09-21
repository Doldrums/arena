// Local Wrangler entrypoint only. Production configuration points to index.ts.
import {route, type Env, json} from './router.ts';
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(request.url).hostname)) {
      return json({error: 'local_development_only'}, 403);
    }
    return route(request, env);
  },
};
