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
  'android/app/build.gradle',
  'android/app/src/main/AndroidManifest.xml',
  'android/gradlew',
  'scripts/prepare-release-signing.sh',
  'keystore.properties.example',
];

for (const rel of required) {
  await access(resolve(root, rel));
}

const configText = await readFile(resolve(root, 'capacitor.config.ts'), 'utf8');
if (!configText.includes('webDir')) {
  throw new Error('capacitor.config.ts must define webDir');
}
if (!configText.includes('../web/build-capacitor')) {
  throw new Error(
    'webDir should point at SvelteKit adapter-static Capacitor output (build-capacitor)'
  );
}
if (!configText.includes("appId: 'de.correlcore.app'")) {
  throw new Error("appId must be 'de.correlcore.app'");
}
if (!configText.includes('cleartext: true')) {
  throw new Error('capacitor.config.ts must allow cleartext for selfhost http:// API URLs');
}
if (!configText.includes("adjustMarginsForEdgeToEdge: 'disable'")) {
  throw new Error(
    'capacitor.config.ts must disable edge-to-edge margins (CSS safe-area owns status-bar inset)'
  );
}

const manifest = await readFile(resolve(root, 'android/app/src/main/AndroidManifest.xml'), 'utf8');
if (!manifest.includes('android:scheme="correlcore"')) {
  throw new Error('AndroidManifest must declare correlcore:// deep link scheme');
}
if (!manifest.includes('android:pathPrefix="/new"')) {
  throw new Error('AndroidManifest must deep-link correlcore://entries/new');
}
if (!manifest.includes('android:usesCleartextTraffic="true"')) {
  throw new Error('AndroidManifest must set usesCleartextTraffic for selfhost HTTP APIs');
}

const pkg = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'));
const versions = [
  pkg.devDependencies?.['@capacitor/android'],
  pkg.devDependencies?.['@capacitor/cli'],
  pkg.devDependencies?.['@capacitor/core'],
];
if (new Set(versions).size !== 1) {
  throw new Error(
    `Capacitor package versions must match (got android=${versions[0]}, cli=${versions[1]}, core=${versions[2]})`
  );
}

const pushVersion = pkg.dependencies?.['@capacitor/push-notifications'];
if (!pushVersion) {
  throw new Error('@capacitor/push-notifications must be listed in dependencies');
}
if (!String(pushVersion).startsWith('7.')) {
  throw new Error(`@capacitor/push-notifications must be Capacitor 7.x (got ${pushVersion})`);
}
if (!manifest.includes('POST_NOTIFICATIONS')) {
  throw new Error('AndroidManifest must declare POST_NOTIFICATIONS for FCM');
}
await access(resolve(root, 'android/app/google-services.json.example'));

console.log('Capacitor Android shell config OK');
