#!/usr/bin/env node
/**
 * CI-friendly Capacitor scaffold check — no Android SDK required.
 */
import { access, readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const required = [
  'capacitor.config.ts',
  'package.json',
  'README.md',
];

for (const rel of required) {
  await access(resolve(root, rel));
}

const configText = await readFile(resolve(root, 'capacitor.config.ts'), 'utf8');
if (!configText.includes('webDir')) {
  throw new Error('capacitor.config.ts must define webDir');
}
if (!configText.includes('../web/build/client')) {
  throw new Error('webDir should point at SvelteKit adapter-node client output');
}

console.log('Capacitor scaffold config OK');
