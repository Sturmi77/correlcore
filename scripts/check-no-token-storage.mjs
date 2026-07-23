/**
 * Guard: no JWTs in web localStorage / sessionStorage (ADR-0006, #453).
 *
 * The persistent-session contract keeps refresh material in HttpOnly cookies on
 * Web/PWA and in Android EncryptedSharedPreferences on Capacitor. Web storage is
 * for UX preferences only. That invariant is currently held by convention; this
 * makes it fail CI instead of silently regressing.
 *
 * Scope and limits: this is a source-level tripwire, not a proof. It flags
 * writes whose storage key or value expression looks token-related, and it
 * requires every storage key to be declared in ALLOWED_KEYS below. It cannot
 * follow a token that is laundered through an unrelated variable name — the
 * allowlist is what makes a new storage key a deliberate, reviewed act.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '..');
const sourceRoot = path.join(repoRoot, 'apps', 'web', 'src');

/**
 * Every key the web app is allowed to put in localStorage / sessionStorage.
 * Adding one is a deliberate decision: it must not hold auth material.
 */
const ALLOWED_KEYS = new Set([
  'cc_analysis_range',
  'cc_entry_open_mode',
  'cc_last_user',
  'cc_offline_client_id',
  'cc_offline_sync_enabled',
  'cc_pwa_dismissed',
  'cc_remember_me',
  'cc_trend_compare_layers',
  'cc_trend_smooth',
  'correlcore-locale',
  'correlcore-theme',
  'correlcore.apiBase',
  'dev_force_viz',
  'dev_mode_enabled',
]);

/**
 * Generic `writeLocal(key, value)` helpers take the key as a parameter, so it
 * cannot be resolved here. Mark those lines `storage-exempt:` with a reason,
 * matching the `token-exempt:` convention in check-style-tokens.mjs. The
 * TOKEN_PATTERN check below still applies to exempt lines.
 */
const STORAGE_EXEMPT = /storage-exempt:/;

/** Identifiers that must never appear in a web-storage write. */
const TOKEN_PATTERN =
  /\b(access[_-]?token|refresh[_-]?token|accessToken|refreshToken|bearer|jwt|password)\b/i;

const STORAGE_WRITE = /\b(?:window\.)?(localStorage|sessionStorage)\.setItem\(([^;]*?)\)/gs;

const failures = [];

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) return walk(full);
    if (/\.(ts|svelte)$/.test(entry.name) && !/\.test\.ts$/.test(entry.name)) return [full];
    return [];
  });
}

/**
 * Map every `CONST = 'literal'` in the web source, so a storage key imported
 * from another module still resolves.
 */
function collectStringConstants(files) {
  const constants = new Map();
  for (const file of files) {
    const source = fs.readFileSync(file, 'utf8');
    for (const match of source.matchAll(
      /\b([A-Za-z_$][\w$]*)\s*(?::\s*string)?\s*=\s*['"`]([^'"`\n]+)['"`]/g
    )) {
      constants.set(match[1], match[2]);
    }
  }
  return constants;
}

/** Resolve `KEY_CONST` / `'literal'` to the string value where we can. */
function resolveKey(expression, constants) {
  const literal = expression.match(/^\s*['"`]([^'"`]+)['"`]/);
  if (literal) return literal[1];

  const identifier = expression.match(/^\s*([A-Za-z_$][\w$]*)\s*,/);
  if (!identifier) return null;
  return constants.get(identifier[1]) ?? null;
}

const sourceFiles = walk(sourceRoot);
const constants = collectStringConstants(sourceFiles);

for (const file of sourceFiles) {
  const source = fs.readFileSync(file, 'utf8');
  const relative = path.relative(repoRoot, file).replace(/\\/g, '/');

  for (const match of source.matchAll(STORAGE_WRITE)) {
    const [, api, args] = match;
    const line = source.slice(0, match.index).split('\n').length;

    if (TOKEN_PATTERN.test(args)) {
      failures.push(`${relative}:${line} — ${api}.setItem writes auth material: ${args.trim()}`);
      continue;
    }

    const lineText = source
      .split('\n')
      .slice(Math.max(0, line - 3), line)
      .join('\n');
    if (STORAGE_EXEMPT.test(lineText)) continue;

    const key = resolveKey(args, constants);
    if (key === null) {
      failures.push(
        `${relative}:${line} — ${api}.setItem key is not a literal or local const, so it ` +
          `cannot be checked against the allowlist. Inline the key, or mark the line ` +
          `\`storage-exempt: <reason>\` if this is a generic write helper.`
      );
    } else if (!ALLOWED_KEYS.has(key)) {
      failures.push(
        `${relative}:${line} — ${api}.setItem uses undeclared key "${key}". ` +
          `Add it to ALLOWED_KEYS in scripts/check-no-token-storage.mjs if it holds no auth material.`
      );
    }
  }
}

if (failures.length > 0) {
  console.error(`Web storage check failed with ${failures.length} issue(s):`);
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Web storage check passed. No auth material in localStorage / sessionStorage.');
