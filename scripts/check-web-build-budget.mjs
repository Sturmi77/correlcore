#!/usr/bin/env node

import { gzipSync } from 'node:zlib';
import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';

const root = process.argv[2] ?? 'apps/web/build/client/_app/immutable';
const limit = Number(process.env.A10_JS_GZIP_BUDGET_BYTES ?? 153_600);

async function filesBelow(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries.map((entry) =>
      entry.isDirectory() ? filesBelow(join(directory, entry.name)) : [join(directory, entry.name)]
    )
  );
  return nested.flat();
}

const javascript = (await filesBelow(root)).filter((path) => path.endsWith('.js'));
if (!javascript.length) throw new Error(`no JavaScript assets found below ${root}`);

const sizes = await Promise.all(
  javascript.map(async (path) => ({ path, gzipBytes: gzipSync(await readFile(path)).byteLength }))
);
const failures = sizes.filter(({ gzipBytes }) => gzipBytes > limit);
for (const { path, gzipBytes } of sizes.sort((a, b) => b.gzipBytes - a.gzipBytes)) {
  console.log(`${gzipBytes.toString().padStart(7)} bytes gzip  ${path}`);
}
if (failures.length) {
  throw new Error(`${failures.length} JavaScript asset(s) exceed the ${limit}-byte gzip budget`);
}
console.log(`${javascript.length} JavaScript assets satisfy the ${limit}-byte gzip budget.`);
