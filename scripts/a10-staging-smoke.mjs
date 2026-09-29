#!/usr/bin/env node

import { randomUUID } from 'node:crypto';
import { writeFile } from 'node:fs/promises';

const baseUrl = required('A10_STAGING_URL').replace(/\/$/, '');
const users = [
  { email: required('A10_USER_A_EMAIL'), password: required('A10_USER_A_PASSWORD') },
  { email: required('A10_USER_B_EMAIL'), password: required('A10_USER_B_PASSWORD') },
];

function required(name) {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required`);
  return value;
}

async function request(path, { token, expected = 200, ...options } = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      accept: 'application/json',
      ...(options.body ? { 'content-type': 'application/json' } : {}),
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (response.status !== expected) {
    throw new Error(
      `${options.method ?? 'GET'} ${path}: expected ${expected}, got ${response.status}`
    );
  }
  const contentType = response.headers.get('content-type') ?? '';
  return contentType.includes('json') ? response.json() : response.text();
}

async function login(user) {
  const body = await request('/api/v1/auth/login?include_access_token=true', {
    method: 'POST',
    body: JSON.stringify({ ...user, remember_me: false }),
  });
  if (!body.access_token) throw new Error(`login for ${user.email} returned no access token`);
  return body.access_token;
}

const [tokenA, tokenB] = await Promise.all(users.map(login));
const [entriesA, entriesB] = await Promise.all([
  request('/api/v1/entries?limit=20', { token: tokenA }),
  request('/api/v1/entries?limit=20', { token: tokenB }),
]);
if (!entriesA.length || !entriesB.length) {
  throw new Error('both release-candidate users need seeded entries');
}

const idsA = new Set(entriesA.map((entry) => entry.id));
if (entriesB.some((entry) => idsA.has(entry.id))) {
  throw new Error('entry ownership isolation failed: users share an entry id');
}

// Exercise capture through a lossless update of an existing seeded entry.
const source = entriesA[0];
const update = {
  mood_score: source.mood_score,
  energy: source.energy,
  stress: source.stress,
  work_context: source.work_context,
  sleep_quality: source.sleep_quality,
  sleep_minutes: source.sleep_minutes,
  cycle_day: source.cycle_day,
  cycle_bleeding_level: source.cycle_bleeding_level,
  note: source.note,
  note_visibility: source.note_visibility,
};
await request(`/api/v1/entries/${source.id}`, {
  token: tokenA,
  method: 'PATCH',
  body: JSON.stringify(update),
});

// A second user must not be able to retrieve the first user's row.
await request(`/api/v1/entries/${source.id}`, { token: tokenB, expected: 404 });

const sync = await request('/api/v1/sync/pull?limit=500', { token: tokenA });
const serializedSync = JSON.stringify(sync);
if (!serializedSync.includes(source.id)) {
  throw new Error('sync pull did not contain the updated entry');
}

const [shortWindow, longWindow, exportJson, insights] = await Promise.all([
  request('/api/v1/entries/stats/timeseries?range=month', { token: tokenA }),
  request('/api/v1/entries/stats/timeseries?range=quarter', { token: tokenA }),
  request('/api/v1/export/json', { token: tokenA }),
  request('/api/v1/insights/latest?limit=10', { token: tokenA }),
]);
if (!shortWindow || !longWindow || !exportJson)
  throw new Error('analysis or export returned no data');

const insight = insights.insights?.find(({ subject_type }) =>
  ['tag', 'symptom'].includes(subject_type)
);
if (!insight?.id) {
  throw new Error('release-candidate user A needs a seeded tag or symptom insight');
}
await Promise.all([
  request(`/api/v1/insights/${insight.id}/event-windows`, { token: tokenA }),
  request(`/api/v1/insights/${insight.id}/verification`, { token: tokenA }),
]);
const dismissal = await request('/api/v1/insights/dismissals', {
  token: tokenA,
  method: 'POST',
  expected: 201,
  body: JSON.stringify({ insight_id: insight.id }),
});
if (!dismissal.id) throw new Error('dismissal response has no id');
await request(`/api/v1/insights/dismissals/${dismissal.id}`, {
  token: tokenA,
  method: 'DELETE',
  expected: 204,
});

const evidence = {
  check: 'real-api-e2e',
  runId: process.env.GITHUB_RUN_ID ?? randomUUID(),
  releaseSha: required('A10_RELEASE_SHA'),
  completedAt: new Date().toISOString(),
  assertions: [
    'two-user-login',
    'entry-capture',
    'owner-isolation',
    'sync-pull',
    'analysis-30d-90d',
    'insight-event-windows',
    'insight-verification',
    'dismissal-round-trip',
    'json-export',
  ],
};
await writeFile(
  process.env.A10_EVIDENCE_FILE ?? 'a10-real-api-e2e.json',
  `${JSON.stringify(evidence, null, 2)}\n`
);
console.log(`A10 staging smoke passed ${evidence.assertions.length} assertions.`);
