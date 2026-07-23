/**
 * Minimal Mock-API für die Browser-Entwicklung ohne echtes Backend.
 *
 * Zweck: Der Dev-Mode-Fixture-Pfad (`$lib/dev/phaseFixtures`) rendert nur,
 * wenn `$auth.status === 'authenticated'` ist — und das hängt an
 * `GET /api/v1/auth/me`. Dieser Server beantwortet genau die Auth-Endpunkte
 * und liefert für alles andere leere Defaults, damit die Fixtures die
 * Darstellung übernehmen.
 *
 * NICHT für Tests von echter API-Logik gedacht: keine Persistenz, keine
 * Validierung, keine Autorisierung. Nur UI-Arbeit im Browser.
 *
 * Start: node scripts/dev-mock-api.mjs   (Port 8001, via MOCK_API_PORT änderbar)
 * Nutzung: INTERNAL_API_URL=http://127.0.0.1:8001 pnpm --filter @correlcore/web dev
 */

import { createServer } from 'node:http';

const PORT = Number(process.env.MOCK_API_PORT ?? 8001);

const USER = {
  id: '00000000-0000-4000-8000-000000000001',
  email: 'dev@correlcore.local',
  display_name: 'Dev User',
  is_verified: true,
};

const TOKENS = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
  expires_in: 3600,
  user: USER,
};

/** Endpunkte, die als leere Liste bzw. leeres Objekt antworten sollen. */
const EMPTY_LIST = ['/tags', '/entries', '/insights', '/habits', '/notes/markers'];

const NOW = new Date().toISOString();

/** Shape: UserPreferencesResponse (apps/web/src/lib/api/preferences.ts). */
const PREFERENCES = {
  user_id: USER.id,
  analytics_enabled: true,
  digest_enabled: false,
  onboarding_retro_completed: true,
  onboarding_profile_completed: true,
  onboarding_maturity_intro_seen: true,
  dismissed_insight_keys: [],
  reached_milestone_keys: [],
  last_seen_insight_at: null,
  created_at: NOW,
  updated_at: NOW,
};

/** Shape: UserProfileResponse (apps/web/src/lib/api/profile.ts). */
const PROFILE = {
  user_id: USER.id,
  sleep_hours_typical: '7h',
  work_context_typical: 'hybrid',
  sport_frequency: '1_2_week',
  insight_curiosity: 'energy_sleep',
  created_at: NOW,
  updated_at: NOW,
};

function send(res, status, body, extraHeaders = {}) {
  const payload = body === null ? '' : JSON.stringify(body);
  res.writeHead(status, {
    'content-type': 'application/json',
    'content-length': Buffer.byteLength(payload),
    ...extraHeaders,
  });
  res.end(payload);
}

const server = createServer((req, res) => {
  const url = new URL(req.url ?? '/', `http://localhost:${PORT}`);
  const path = url.pathname.replace(/^\/api\/v1/, '');
  const method = req.method ?? 'GET';

  // Request-Body verwerfen — nichts davon wird ausgewertet.
  req.resume();

  if (method === 'OPTIONS') {
    return send(res, 204, null, {
      'access-control-allow-origin': '*',
      'access-control-allow-headers': '*',
      'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
    });
  }

  if (path === '/auth/me' && method === 'GET') {
    return send(res, 200, USER);
  }

  if ((path === '/auth/login' || path === '/auth/refresh') && method === 'POST') {
    // Cookie-Pfad (Browser-Build) und Bearer-Pfad (Capacitor-Build) zugleich bedienen.
    return send(res, 200, TOKENS, {
      'set-cookie': [
        'access_token=mock-access-token; Path=/; HttpOnly; SameSite=Lax',
        'refresh_token=mock-refresh-token; Path=/; HttpOnly; SameSite=Lax',
      ],
    });
  }

  if (path === '/auth/logout' && method === 'POST') {
    return send(
      res,
      200,
      { message: 'ok' },
      {
        'set-cookie': ['access_token=; Path=/; Max-Age=0', 'refresh_token=; Path=/; Max-Age=0'],
      }
    );
  }

  if (path === '/user/preferences') {
    // PUT/PATCH quittieren, ohne etwas zu merken — reicht fuer UI-Klickwege.
    return send(res, 200, PREFERENCES);
  }

  if (path === '/user/profile') {
    return send(res, 200, PROFILE);
  }

  if (path === '/health' || path === '/healthz') {
    return send(res, 200, { status: 'ok' });
  }

  if (method === 'GET' && EMPTY_LIST.some((prefix) => path.startsWith(prefix))) {
    return send(res, 200, []);
  }

  // Alles Übrige bewusst als 404 — die Seiten fallen dann auf ihren
  // Leer-/Fehlerzustand zurück statt auf erfundene Datenformen.
  console.log(`[mock-api] 404 ${method} ${url.pathname}`);
  return send(res, 404, { detail: 'mock-api: not implemented' });
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`[mock-api] listening on http://127.0.0.1:${PORT} (user: ${USER.email})`);
});
