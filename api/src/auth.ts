import {createRemoteJWKSet, jwtVerify, type JWTVerifyGetKey} from 'jose';

export interface AccessConfig {
  ACCESS_TEAM_DOMAIN?: string;
  ACCESS_AUD?: string;
}
const keySets = new Map<string, JWTVerifyGetKey>();

export function accessIssuer(config: AccessConfig): string | null {
  const domain = config.ACCESS_TEAM_DOMAIN;
  if (!domain || !config.ACCESS_AUD) return null;
  // Configuration is an origin, never an arbitrary URL supplied by a request.
  if (!/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com\/?$/.test(domain)) return null;
  return domain.replace(/\/$/, '');
}

export async function verifyAccessToken(token: string, config: AccessConfig, keys?: JWTVerifyGetKey) {
  const issuer = accessIssuer(config);
  if (!issuer) throw new Error('Access is not configured');
  let resolver = keys ?? keySets.get(issuer);
  if (!resolver) {
    resolver = createRemoteJWKSet(new URL(`${issuer}/cdn-cgi/access/certs`));
    keySets.set(issuer, resolver);
  }
  return (await jwtVerify(token, resolver, {
    issuer, audience: config.ACCESS_AUD, algorithms: ['RS256'],
    requiredClaims: ['exp', 'iat', 'sub'],
  })).payload;
}
