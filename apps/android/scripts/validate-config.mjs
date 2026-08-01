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
if (!/allowMixedContent:\s*true/.test(configText)) {
  throw new Error(
    'capacitor.config.ts must set allowMixedContent: true — https://localhost WebView otherwise blocks http:// API fetches (mixed content)'
  );
}
// Cap 8 removed android.adjustMarginsForEdgeToEdge; safe-area is CSS-owned
// (apps/web app.css). Do not reintroduce the Cap-7-only config key.

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
if (!manifest.includes('android:allowBackup="false"')) {
  throw new Error(
    'AndroidManifest must set allowBackup=false — WebView/IndexedDB holds health-adjacent offline data'
  );
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
if (!String(pushVersion).startsWith('8.')) {
  throw new Error(`@capacitor/push-notifications must be Capacitor 8.x (got ${pushVersion})`);
}
if (!manifest.includes('POST_NOTIFICATIONS')) {
  throw new Error('AndroidManifest must declare POST_NOTIFICATIONS for FCM');
}
await access(resolve(root, 'android/app/google-services.json.example'));
await access(
  resolve(root, 'android/app/src/main/java/de/correlcore/app/push/PushAvailabilityPlugin.kt')
);

const appGradle = await readFile(resolve(root, 'android/app/build.gradle'), 'utf8');
if (!appGradle.includes('buildConfigField "boolean", "FCM_ENABLED"')) {
  throw new Error(
    'app/build.gradle must expose BuildConfig.FCM_ENABLED for PushAvailability gating'
  );
}

const mainActivity = await readFile(
  resolve(root, 'android/app/src/main/java/de/correlcore/app/MainActivity.java'),
  'utf8'
);
if (!mainActivity.includes('PushAvailabilityPlugin')) {
  throw new Error('MainActivity must register PushAvailabilityPlugin');
}

console.log('Capacitor Android shell config OK');
