import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const appCssPath = path.join(root, 'apps', 'web', 'src', 'app.css');
const appSourcePath = path.join(root, 'apps');
const appCss = fs.readFileSync(appCssPath, 'utf8');

const requiredTokens = [
  '--color-gold',
  '--color-insight-early',
  '--color-insight-provisional',
  '--color-insight-robust',
  '--color-metric-mood',
  '--color-metric-energy',
  '--color-metric-stress',
];

const informationalPairs = [
  ['dark', '--color-text', '--color-bg', 4.5],
  ['dark', '--color-text-muted', '--color-bg', 4.5],
  ['dark', '--color-primary', '--color-bg', 4.5],
  ['dark', '--color-gold', '--color-bg', 4.5],
  ['dark', '--color-insight-early', '--color-bg', 4.5],
  ['dark', '--color-insight-provisional', '--color-bg', 4.5],
  ['light', '--color-text', '--color-bg', 4.5],
  ['light', '--color-text-muted', '--color-bg', 4.5],
  ['light', '--color-primary', '--color-bg', 4.5],
  ['light', '--color-primary-hover', '--color-bg', 4.5],
  ['light', '--color-primary-active', '--color-bg', 4.5],
  ['light', '--color-gold', '--color-bg', 4.5],
  ['light', '--color-insight-early', '--color-bg', 4.5],
  ['light', '--color-insight-provisional', '--color-bg', 4.5],
];

const uiPairs = [
  ['dark', '--color-primary', '--color-surface', 3],
  ['dark', '--color-primary', '--color-surface-2', 3],
  ['dark', '--color-success', '--color-bg', 3],
  ['dark', '--color-error', '--color-bg', 3],
  ['dark', '--color-insight-robust', '--color-bg', 3],
  ['light', '--color-primary', '--color-surface', 3],
  ['light', '--color-primary', '--color-surface-2', 3],
  ['light', '--color-success', '--color-bg', 3],
  ['light', '--color-error', '--color-bg', 3],
  ['light', '--color-insight-robust', '--color-bg', 3],
];

const failures = [];

function extractBlock(label, startPattern) {
  const start = appCss.search(startPattern);
  if (start === -1) {
    failures.push(`Missing ${label} token block.`);
    return '';
  }

  const open = appCss.indexOf('{', start);
  let depth = 0;
  for (let index = open; index < appCss.length; index += 1) {
    const char = appCss[index];
    if (char === '{') {
      depth += 1;
    }
    if (char === '}') {
      depth -= 1;
    }
    if (depth === 0) {
      return appCss.slice(open + 1, index);
    }
  }

  failures.push(`Could not parse ${label} token block.`);
  return '';
}

function parseTokens(block) {
  const tokens = new Map();
  const tokenRegex = /(--[a-z0-9-]+)\s*:\s*([^;]+);/gi;
  for (const match of block.matchAll(tokenRegex)) {
    tokens.set(match[1], match[2].trim());
  }
  return tokens;
}

const dark = parseTokens(extractBlock('dark', /:root,\s*\n\[data-theme='dark'\]\s*\{/));
const light = parseTokens(extractBlock('light', /\[data-theme='light'\]\s*\{/));
const fallback = parseTokens(
  extractBlock('system dark fallback', /:root:not\(\[data-theme\]\)\s*\{/)
);

for (const token of requiredTokens) {
  if (!dark.has(token)) {
    failures.push(`Missing ${token} in dark theme.`);
  }
  if (!light.has(token)) {
    failures.push(`Missing ${token} in light theme.`);
  }
  if (!fallback.has(token)) {
    failures.push(`Missing ${token} in system dark fallback.`);
  }
}

for (const [token, value] of dark.entries()) {
  if (!fallback.has(token)) {
    failures.push(`System dark fallback is missing ${token}.`);
    continue;
  }
  if (fallback.get(token) !== value) {
    failures.push(
      `System dark fallback differs for ${token}: expected "${value}", got "${fallback.get(token)}".`
    );
  }
}

for (const token of fallback.keys()) {
  if (!dark.has(token)) {
    failures.push(`System dark fallback has extra token ${token}.`);
  }
}

const legacyReferences = findFiles(appSourcePath)
  .filter((file) => /\.(css|svelte|ts|js|json)$/.test(file))
  .filter((file) => fs.readFileSync(file, 'utf8').includes('color-ms-primary'));

if (legacyReferences.length > 0) {
  failures.push(
    `Legacy --color-ms-primary* references remain:\n${legacyReferences
      .map((file) => `  - ${path.relative(root, file)}`)
      .join('\n')}`
  );
}

if (
  informationalPairs.some(
    ([, foreground, background]) =>
      foreground === '--color-text-faint' || background === '--color-text-faint'
  )
) {
  failures.push('--color-text-faint must not be part of informational contrast assertions.');
}

checkPairs('informational text', informationalPairs);
checkPairs('non-text UI', uiPairs);

if (failures.length > 0) {
  console.error(`Contrast check failed with ${failures.length} issue(s):`);
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log('Contrast check passed.');
console.log(
  'Note: --color-text-faint is decorative-only and intentionally excluded from text-pair assertions.'
);

function checkPairs(groupName, pairs) {
  for (const [theme, foregroundToken, backgroundToken, minimum] of pairs) {
    const tokens = theme === 'dark' ? dark : light;
    const foreground = tokens.get(foregroundToken);
    const background = tokens.get(backgroundToken);

    if (!foreground || !background) {
      failures.push(
        `Missing pair token for ${groupName}: ${theme} ${foregroundToken} on ${backgroundToken}.`
      );
      continue;
    }

    if (!isHexColor(foreground) || !isHexColor(background)) {
      failures.push(
        `Pair uses non-hex token value for ${groupName}: ${theme} ${foregroundToken} on ${backgroundToken}.`
      );
      continue;
    }

    const actual = contrastRatio(foreground, background);
    if (actual < minimum) {
      failures.push(
        `${theme} ${groupName} contrast ${foregroundToken} (${foreground}) on ${backgroundToken} (${background}) is ${actual.toFixed(
          2
        )}:1; expected at least ${minimum}:1.`
      );
    }
  }
}

function isHexColor(value) {
  return /^#[0-9a-f]{6}$/i.test(value);
}

function contrastRatio(foreground, background) {
  const foregroundLuminance = relativeLuminance(foreground);
  const backgroundLuminance = relativeLuminance(background);
  const lighter = Math.max(foregroundLuminance, backgroundLuminance);
  const darker = Math.min(foregroundLuminance, backgroundLuminance);
  return (lighter + 0.05) / (darker + 0.05);
}

function relativeLuminance(hex) {
  const [red, green, blue] = hex
    .slice(1)
    .match(/.{2}/g)
    .map((channel) => parseInt(channel, 16) / 255)
    .map((channel) =>
      channel <= 0.03928 ? channel / 12.92 : Math.pow((channel + 0.055) / 1.055, 2.4)
    );

  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function findFiles(directory) {
  const entries = fs.readdirSync(directory, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return findFiles(fullPath);
    }
    return fullPath;
  });
}
