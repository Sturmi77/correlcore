import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

export class DuplicateJsonKeyError extends SyntaxError {
  constructor(file, key, objectPath) {
    super(`${file}: duplicate JSON key ${JSON.stringify(key)} at ${objectPath}`);
    this.name = 'DuplicateJsonKeyError';
  }
}

/**
 * Inspect raw JSON before JSON.parse can discard duplicate object members.
 * String tokens are decoded independently so escaped and literal spellings of
 * the same key are treated as duplicates.
 */
export function assertNoDuplicateJsonKeys(source, file = '<json>') {
  let index = 0;

  function fail(message) {
    throw new SyntaxError(`${file}: ${message} at offset ${index}`);
  }

  function skipWhitespace() {
    while (index < source.length && /\s/u.test(source[index])) index += 1;
  }

  function readString() {
    if (source[index] !== '"') fail('expected a JSON string');
    const start = index;
    index += 1;
    while (index < source.length) {
      const char = source[index];
      if (char === '\\') {
        index += 2;
        continue;
      }
      index += 1;
      if (char === '"') {
        return JSON.parse(source.slice(start, index));
      }
    }
    fail('unterminated JSON string');
  }

  function expect(char) {
    skipWhitespace();
    if (source[index] !== char) fail(`expected ${JSON.stringify(char)}`);
    index += 1;
  }

  function readScalar() {
    const start = index;
    while (index < source.length && !/[\s,}\]]/u.test(source[index])) index += 1;
    if (start === index) fail('expected a JSON value');
  }

  function readValue(currentPath) {
    skipWhitespace();
    const char = source[index];
    if (char === '{') return readObject(currentPath);
    if (char === '[') return readArray(currentPath);
    if (char === '"') {
      readString();
      return;
    }
    readScalar();
  }

  function readObject(currentPath) {
    expect('{');
    skipWhitespace();
    if (source[index] === '}') {
      index += 1;
      return;
    }

    const keys = new Set();
    while (index < source.length) {
      skipWhitespace();
      const key = readString();
      if (keys.has(key)) throw new DuplicateJsonKeyError(file, key, currentPath);
      keys.add(key);
      expect(':');
      readValue(`${currentPath}.${key}`);
      skipWhitespace();
      if (source[index] === '}') {
        index += 1;
        return;
      }
      expect(',');
    }
    fail('unterminated JSON object');
  }

  function readArray(currentPath) {
    expect('[');
    skipWhitespace();
    if (source[index] === ']') {
      index += 1;
      return;
    }

    let item = 0;
    while (index < source.length) {
      readValue(`${currentPath}[${item}]`);
      skipWhitespace();
      if (source[index] === ']') {
        index += 1;
        return;
      }
      expect(',');
      item += 1;
    }
    fail('unterminated JSON array');
  }

  readValue('$');
  skipWhitespace();
  if (index !== source.length) fail('unexpected trailing content');
}

function flattenKeys(value, prefix = '') {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return [prefix];
  return Object.entries(value).flatMap(([key, child]) =>
    flattenKeys(child, prefix ? `${prefix}.${key}` : key)
  );
}

export async function validateLocaleFiles(files) {
  const sources = await Promise.all(files.map((file) => readFile(file, 'utf8')));

  // Keep this pass separate and first: JSON.parse would already have lost the
  // duplicate member and could only validate the last value.
  sources.forEach((source, position) => assertNoDuplicateJsonKeys(source, files[position]));

  const locales = sources.map((source) => JSON.parse(source));
  const expected = flattenKeys(locales[0]).sort();
  for (let position = 1; position < locales.length; position += 1) {
    const actual = flattenKeys(locales[position]).sort();
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {
      const expectedSet = new Set(expected);
      const actualSet = new Set(actual);
      const missing = expected.filter((key) => !actualSet.has(key));
      const extra = actual.filter((key) => !expectedSet.has(key));
      throw new Error(
        `${files[position]}: locale keys differ; missing=${JSON.stringify(missing)}, extra=${JSON.stringify(extra)}`
      );
    }
  }
}

const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), '..');
const defaultFiles = ['de.json', 'en.json'].map((name) =>
  path.join(repoRoot, 'apps', 'web', 'src', 'lib', 'i18n', 'locales', name)
);

if (process.argv[1] && path.resolve(process.argv[1]) === scriptPath) {
  const files = process.argv.slice(2);
  validateLocaleFiles(files.length > 0 ? files.map((file) => path.resolve(file)) : defaultFiles)
    .then(() => console.log('Locale JSON has unique, matching keys.'))
    .catch((error) => {
      console.error(error instanceof Error ? error.message : error);
      process.exitCode = 1;
    });
}
