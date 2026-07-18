import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '..');
const webRoot = path.join(repoRoot, 'apps', 'web');
const appCssPath = path.join(webRoot, 'src', 'app.css');
const sourceRoot = path.join(webRoot, 'src');

const CANONICAL_BREAKPOINTS_PX = new Set([360, 480, 767, 768, 1024]);
const LOCAL_VAR_PREFIXES = ['--bar-', '--tag-', '--metric-', '--axis-', '--insight-accent'];
const LOCAL_VAR_EXACT = new Set([
  '--day-count',
  '--habit-progress',
  '--timeseries-chart-width',
  '--week-count',
  '--strip-chart-width',
  '--tag-count',
]);

// Brand-mark sizes must use BRAND_MARK_* constants from iconSizes.ts — no
// numeric size={} literals on CorrelCoreLogo (legacy 40/72 exempt removed).
const TOKEN_EXEMPT = /token-exempt:/;

const failures = [];
const appCss = fs.readFileSync(appCssPath, 'utf8');

function parseDefinedTokens(css) {
  const tokens = new Set();
  for (const match of css.matchAll(/(--[a-z0-9-]+)\s*:/gi)) {
    tokens.add(match[1]);
  }
  return tokens;
}

const definedTokens = parseDefinedTokens(appCss);

function findSvelteFiles(directory) {
  const entries = fs.readdirSync(directory, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return findSvelteFiles(fullPath);
    if (entry.name.endsWith('.svelte')) return [fullPath];
    return [];
  });
}

function isAllowedLocalVar(token) {
  if (LOCAL_VAR_EXACT.has(token)) return true;
  return LOCAL_VAR_PREFIXES.some((prefix) => token.startsWith(prefix));
}

function extractStyleBlocks(content) {
  const blocks = [];
  const regex = /<style[^>]*>([\s\S]*?)<\/style>/gi;
  for (const match of content.matchAll(regex)) {
    blocks.push(match[1]);
  }
  return blocks;
}

function hasRecentExempt(lines, lineIndex) {
  const start = Math.max(0, lineIndex - 3);
  return lines.slice(start, lineIndex + 1).some((line) => TOKEN_EXEMPT.test(line));
}

function checkBreakpoints(line, relative, lineNumber) {
  for (const match of line.matchAll(/@media\s*\([^)]*(min|max)-width:\s*([0-9.]+)(px|rem)/g)) {
    const value = Number(match[2]);
    const unit = match[3];
    const px = unit === 'rem' ? value * 16 : value;
    const rounded = Math.round(px);
    if (!CANONICAL_BREAKPOINTS_PX.has(rounded)) {
      failures.push(`Non-canonical breakpoint ${match[0]} in ${relative}:${lineNumber}`);
    }
  }
}

function checkStyleBlock(block, relative) {
  const lines = block.split('\n');
  const blockExempt = lines.slice(0, 5).some((line) => /token-exempt-block:/.test(line));

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const lineNumber = index + 1;
    const exempt = blockExempt || hasRecentExempt(lines, index);

    checkBreakpoints(line, relative, lineNumber);

    if (
      /(?:^|[^a-z-])(#[0-9a-fA-F]{3,8})\b/.test(line) &&
      /(color|background|border|fill|stroke)\s*:/.test(line) &&
      !exempt
    ) {
      failures.push(`Hex color literal in ${relative} style block line ${lineNumber}`);
    }

    if (/font-size:\s*[0-9.]+rem/.test(line) && !exempt) {
      failures.push(
        `Hardcoded font-size rem literal in ${relative} style block line ${lineNumber}`
      );
    }

    if (/font-size:\s*[0-9.]+px/.test(line) && !exempt) {
      failures.push(`Hardcoded font-size px literal in ${relative} style block line ${lineNumber}`);
    }

    if (/border-radius:\s*[0-9]/.test(line) && !exempt) {
      if (!/border-radius:\s*0(?:\s|;|$)/.test(line)) {
        failures.push(
          `Hardcoded border-radius literal in ${relative} style block line ${lineNumber}`
        );
      }
    }

    if (/border-radius:\s*999px/.test(line) && !exempt) {
      failures.push(`Hardcoded pill radius 999px in ${relative} style block line ${lineNumber}`);
    }
  }
}

for (const file of findSvelteFiles(sourceRoot)) {
  const content = fs.readFileSync(file, 'utf8');
  const relative = path.relative(repoRoot, file);

  for (const match of content.matchAll(/size=\{([0-9]+)\}/g)) {
    failures.push(
      `Icon size literal size={${match[1]}} in ${relative} — use ICON_SIZE_SM/MD or BRAND_MARK_*`
    );
  }

  for (const match of content.matchAll(/var\((--[a-z0-9-]+)\)/g)) {
    const token = match[1];
    if (!definedTokens.has(token) && !isAllowedLocalVar(token)) {
      failures.push(`Undefined CSS variable ${token} in ${relative}`);
    }
  }

  for (const block of extractStyleBlocks(content)) {
    checkStyleBlock(block, relative);
  }
}

const uniqueFailures = [...new Set(failures)];

if (uniqueFailures.length > 0) {
  console.error(`Style token check failed with ${uniqueFailures.length} issue(s):`);
  for (const failure of uniqueFailures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log('Style token check passed.');
