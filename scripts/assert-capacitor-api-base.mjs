#!/usr/bin/env node
/**
 * Fail Capacitor release builds when VITE_API_BASE_URL is missing or relative.
 *
 * Relative `/api/v1` resolves to `https://localhost/api/v1` inside the Android
 * WebView (androidScheme: https) — login then fails with a generic network error.
 *
 * Usage (CI release job):
 *   VITE_API_BASE_URL=https://host.example/api/v1 node scripts/assert-capacitor-api-base.mjs
 */

const raw = (process.env.VITE_API_BASE_URL ?? '').trim();

function fail(message) {
  console.error(`assert-capacitor-api-base: ${message}`);
  process.exit(1);
}

if (!raw) {
  fail(
    'VITE_API_BASE_URL is required for signed Capacitor builds. ' +
      'Set repository secret/variable VITE_API_BASE_URL or the workflow_dispatch input ' +
      'vite_api_base_url (must be absolute http(s) ending with /api/v1).'
  );
}

if (raw.startsWith('/')) {
  fail(
    `VITE_API_BASE_URL must be absolute, got relative "${raw}". ` +
      'Example: https://your-host.example/api/v1'
  );
}

let parsed;
try {
  parsed = new URL(raw);
} catch {
  fail(`VITE_API_BASE_URL is not a valid URL: "${raw}"`);
}

if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
  fail(`VITE_API_BASE_URL must use http(s), got protocol "${parsed.protocol}"`);
}

const normalized = raw.replace(/\/+$/, '');
if (!normalized.endsWith('/api/v1')) {
  fail(`VITE_API_BASE_URL must end with /api/v1, got "${normalized}"`);
}

console.log(`assert-capacitor-api-base: OK (${normalized})`);
