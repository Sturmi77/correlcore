import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import {
  DuplicateJsonKeyError,
  assertNoDuplicateJsonKeys,
  validateLocaleFiles,
} from './check-locale-json.mjs';

const scriptsDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptsDir, '..');

test('rejects the intentionally duplicated locale fixture before JSON.parse', async () => {
  const fixture = path.join(scriptsDir, 'fixtures', 'locale-duplicate.json');
  const source = await readFile(fixture, 'utf8');
  assert.throws(
    () => assertNoDuplicateJsonKeys(source, fixture),
    (error) =>
      error instanceof DuplicateJsonKeyError &&
      error.message.includes('check_question') &&
      error.message.includes('$.trends.compare')
  );
});

test('treats escaped and literal spellings as the same object key', () => {
  assert.throws(
    () => assertNoDuplicateJsonKeys('{"check_question": 1, "check\\u005fquestion": 2}'),
    DuplicateJsonKeyError
  );
});

test('allows the same key in separate objects', () => {
  assert.doesNotThrow(() => assertNoDuplicateJsonKeys('{"a":{"key":1},"b":{"key":2}}'));
});

test('current DE and EN locale files have unique, matching keys', async () => {
  await validateLocaleFiles(
    ['de.json', 'en.json'].map((name) =>
      path.join(repoRoot, 'apps', 'web', 'src', 'lib', 'i18n', 'locales', name)
    )
  );
});
