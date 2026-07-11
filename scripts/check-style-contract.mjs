import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const appCssPath = path.join(root, 'apps', 'web', 'src', 'app.css');
const appSourcePath = path.join(root, 'apps', 'web', 'src');

const ALLOWED_BUTTON_VARIANTS = new Set(['primary', 'secondary', 'ghost', 'danger', 'link']);
const ALLOWED_PANEL_VARIANTS = new Set(['plain', 'bordered', 'elevated', 'chart', 'danger']);
const ALLOWED_INLINE_ALERT_VARIANTS = new Set(['info', 'success', 'warning', 'error']);

const ALLOWED_BUTTON_CLASS_SUFFIXES = new Set([
  ...ALLOWED_BUTTON_VARIANTS,
  'sm',
  'md',
  'lg',
  'full',
  'stacked',
  'icon-only',
]);

const failures = [];
const appCss = fs.readFileSync(appCssPath, 'utf8');

function extractThemeBlocks(css) {
  const blocks = [];
  const patterns = [
    /:root,\s*\n\[data-theme='dark'\]\s*\{/,
    /\[data-theme='light'\]\s*\{/,
    /:root:not\(\[data-theme\]\)\s*\{/,
  ];

  for (const pattern of patterns) {
    const start = css.search(pattern);
    if (start === -1) {
      failures.push(`Missing theme block for pattern ${pattern}`);
      continue;
    }
    const open = css.indexOf('{', start);
    let depth = 0;
    for (let index = open; index < css.length; index += 1) {
      const char = css[index];
      if (char === '{') depth += 1;
      if (char === '}') depth -= 1;
      if (depth === 0) {
        blocks.push(css.slice(open + 1, index));
        break;
      }
    }
  }

  return blocks;
}

function parseColorTokens(blocks) {
  const tokens = new Set();
  const tokenRegex = /(--color-[a-z0-9-]+)\s*:/gi;
  for (const block of blocks) {
    for (const match of block.matchAll(tokenRegex)) {
      tokens.add(match[1]);
    }
  }
  return tokens;
}

function findSourceFiles(directory) {
  const entries = fs.readdirSync(directory, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return findSourceFiles(fullPath);
    }
    if (/\.(css|svelte|ts|js)$/.test(entry.name)) {
      return [fullPath];
    }
    return [];
  });
}

const themeBlocks = extractThemeBlocks(appCss);
const allowedColorTokens = parseColorTokens(themeBlocks);

for (const file of findSourceFiles(appSourcePath)) {
  const content = fs.readFileSync(file, 'utf8');
  const relative = path.relative(root, file);

  for (const match of content.matchAll(/var\((--color-[a-z0-9-]+)\)/g)) {
    const token = match[1];
    if (!allowedColorTokens.has(token)) {
      failures.push(`Unknown color token ${token} in ${relative}`);
    }
  }

  for (const match of content.matchAll(/ui-button--([a-z]+(?:-[a-z]+)?)/g)) {
    const suffix = match[1];
    if (!ALLOWED_BUTTON_CLASS_SUFFIXES.has(suffix)) {
      failures.push(`Unknown Button class suffix "${suffix}" in ${relative}`);
    }
  }

  for (const match of content.matchAll(/ui-panel--([a-z]+)/g)) {
    const variant = match[1];
    if (!ALLOWED_PANEL_VARIANTS.has(variant)) {
      failures.push(`Unknown Panel variant "${variant}" in ${relative}`);
    }
  }

  for (const match of content.matchAll(/inline-alert--([a-z]+)/g)) {
    const variant = match[1];
    if (!ALLOWED_INLINE_ALERT_VARIANTS.has(variant)) {
      failures.push(`Unknown InlineAlert variant "${variant}" in ${relative}`);
    }
  }

  const lines = content.split('\n');
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const variantMatch = line.match(/\bvariant=["']([^"']+)["']/);
    if (!variantMatch) continue;

    const value = variantMatch[1];

    if (/<Button\b/.test(line)) {
      if (!ALLOWED_BUTTON_VARIANTS.has(value)) {
        failures.push(`Unknown Button variant "${value}" in ${relative}:${index + 1}`);
      }
      continue;
    }
    if (/<Panel\b/.test(line)) {
      if (!ALLOWED_PANEL_VARIANTS.has(value)) {
        failures.push(`Unknown Panel variant "${value}" in ${relative}:${index + 1}`);
      }
      continue;
    }
    if (/<InlineAlert\b/.test(line)) {
      if (!ALLOWED_INLINE_ALERT_VARIANTS.has(value)) {
        failures.push(`Unknown InlineAlert variant "${value}" in ${relative}:${index + 1}`);
      }
    }
  }
}

const uniqueFailures = [...new Set(failures)];

if (uniqueFailures.length > 0) {
  console.error(`Style contract check failed with ${uniqueFailures.length} issue(s):`);
  for (const failure of uniqueFailures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log('Style contract check passed.');
console.log(`Validated ${allowedColorTokens.size} color tokens and shared component variants.`);
