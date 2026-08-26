/**
 * Regenerates phase-matrix + marketing screenshots from Dev Mode fixtures
 * (personaDataset via phaseFixtures) and the anonymous landing.
 *
 * Run (from apps/web):
 *   CAPTURE_SCREENSHOTS=1 pnpm exec playwright test tests/e2e/capture-phase-screenshots.spec.ts
 */
import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { installInsightsApiMock } from './helpers/insightsApiMock';

const enabled = process.env.CAPTURE_SCREENSHOTS === '1';
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const phaseDir = path.join(repoRoot, 'docs/assets/phase_matrix/screenshots');
const marketingDir = path.join(repoRoot, 'docs/assets/screenshots');
const thumbDocDir = path.join(phaseDir, 'onboarding_expectation');
const thumbStaticDir = path.join(repoRoot, 'apps/web/static/onboarding/maturity');

const PHASES = ['collecting', 'early_patterns', 'provisional', 'robust'] as const;

test.describe('phase / marketing screenshot capture', () => {
  test.skip(!enabled, 'Set CAPTURE_SCREENSHOTS=1 to regenerate PNGs');

  test('capture mobile phase progression + robust lead + landing marketing shots', async ({
    browser,
  }) => {
    test.setTimeout(180_000);
    fs.mkdirSync(phaseDir, { recursive: true });
    fs.mkdirSync(marketingDir, { recursive: true });
    fs.mkdirSync(thumbDocDir, { recursive: true });
    fs.mkdirSync(thumbStaticDir, { recursive: true });

    const mobile = await browser.newContext({
      viewport: { width: 390, height: 844 },
      deviceScaleFactor: 3,
      hasTouch: true,
      colorScheme: 'dark',
      locale: 'de-DE',
    });
    const mobilePage = await mobile.newPage();
    await prepareDevSession(mobilePage);

    for (const phase of PHASES) {
      await setPhaseViaDevUi(mobilePage, phase);
      await openInsightsViaNav(mobilePage);
      await expectPhaseSurface(mobilePage, phase);
      await mobilePage.waitForTimeout(700);
      await mobilePage.screenshot({
        path: path.join(phaseDir, `mobile__InsightsPage__${phase}.png`),
        fullPage: false,
      });
    }

    await setPhaseViaDevUi(mobilePage, 'robust');
    await openInsightsViaNav(mobilePage);
    const lead = mobilePage.getByTestId('mobile-insight-lead');
    await expect(lead).toBeVisible({ timeout: 30_000 });
    await lead.screenshot({
      path: path.join(phaseDir, 'mobile__MobileInsightLead__robust.png'),
    });

    await mobile.close();

    await cropSquareThumb(
      path.join(phaseDir, 'mobile__InsightsPage__collecting.png'),
      'phase1_collecting'
    );
    await cropSquareThumb(
      path.join(phaseDir, 'mobile__InsightsPage__early_patterns.png'),
      'phase2_early_patterns'
    );
    await cropSquareThumb(
      path.join(phaseDir, 'mobile__InsightsPage__provisional.png'),
      'phase3_provisional'
    );
    await cropSquareThumb(
      path.join(phaseDir, 'mobile__MobileInsightLead__robust.png'),
      'phase4_robust'
    );

    const desktop = await browser.newContext({
      viewport: { width: 1440, height: 1600 },
      deviceScaleFactor: 2,
      colorScheme: 'dark',
      locale: 'de-DE',
    });
    const desk = await desktop.newPage();
    await desk.route('**/api/v1/instance', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          mode: 'hosted',
          registration_enabled: true,
          version: 'capture',
        }),
      });
    });
    await desk.addInitScript(() => {
      localStorage.setItem('correlcore-locale', 'de');
    });
    await desk.goto('/');
    await expect(desk.getByTestId('marketing-landing')).toBeVisible({ timeout: 30_000 });
    await desk.waitForTimeout(1000);

    await desk.getByTestId('landing-weekday').scrollIntoViewIfNeeded();
    await desk
      .getByTestId('landing-weekday')
      .screenshot({ path: path.join(marketingDir, 'weekday.png') });

    await desk.locator('.landing__previews').scrollIntoViewIfNeeded();
    await desk
      .locator('.landing__previews')
      .screenshot({ path: path.join(marketingDir, 'insights.png') });

    await desk.getByTestId('landing-journey').scrollIntoViewIfNeeded();
    await desk.getByTestId('landing-journey').screenshot({
      path: path.join(phaseDir, 'landing__Journey__maturity.png'),
    });

    await desktop.close();
  });
});

async function prepareDevSession(page: Page): Promise<void> {
  await installInsightsApiMock(page);
  await page.route('**/api/v1/dev/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        git_commit: 'capture',
        version: 'capture',
        app_env: 'development',
        deployment_mode: 'selfhost',
      }),
    });
  });
  await page.addInitScript(() => {
    localStorage.setItem('dev_mode_enabled', 'true');
    localStorage.setItem('dev_force_viz', 'true');
    localStorage.setItem('correlcore-locale', 'de');
  });
  await openDevViz(page);
}

async function openDevViz(page: Page): Promise<void> {
  await page.goto('/dev');
  await page.getByTestId('dev-tab-devviz').click();
  await expect(page.getByTestId('developer-toggle')).toBeVisible({ timeout: 30_000 });
  const mode = page.getByTestId('developer-toggle');
  if (!(await mode.isChecked())) await mode.check();
  const force = page.getByTestId('force-viz-toggle');
  await expect(force).toBeVisible();
  if (!(await force.isChecked())) await force.check();
  await expect(mode).toBeChecked();
  await expect(force).toBeChecked();
  await expect(page.getByTestId('developer-phase-select')).toBeVisible();
}

async function setPhaseViaDevUi(page: Page, phase: (typeof PHASES)[number]): Promise<void> {
  if (!page.url().includes('/dev')) {
    await page.locator('nav a[href="/settings"]').first().click();
    await page.waitForURL('**/settings**');
    await page.getByTestId('dev-link').click();
    await page.waitForURL('**/dev**');
  }
  await page.getByTestId('dev-tab-devviz').click();
  const mode = page.getByTestId('developer-toggle');
  if (!(await mode.isChecked())) await mode.check();
  const force = page.getByTestId('force-viz-toggle');
  if (!(await force.isChecked())) await force.check();
  await page.getByTestId('developer-phase-select').selectOption(phase);
  await expect(page.getByTestId('developer-phase-select')).toHaveValue(phase);
  await page.waitForTimeout(150);
}

async function openInsightsViaNav(page: Page): Promise<void> {
  await page.locator('nav a[href="/insights"]').first().click();
  await page.waitForURL('**/insights**');
  await expect(page.locator('main.insights-page')).toBeVisible({ timeout: 30_000 });
}

async function expectPhaseSurface(page: Page, phase: (typeof PHASES)[number]): Promise<void> {
  if (phase === 'collecting') {
    await expect(page.getByText(/Daten sammeln|3\/7/i).first()).toBeVisible({ timeout: 30_000 });
    return;
  }
  await expect(page.getByTestId('mobile-insight-lead')).toBeVisible({ timeout: 30_000 });
}

async function cropSquareThumb(sourcePath: string, basename: string): Promise<void> {
  const { createRequire } = await import('node:module');
  const require = createRequire(import.meta.url);
  let sharp: typeof import('sharp') | null = null;
  try {
    sharp = require('sharp');
  } catch {
    sharp = null;
  }

  const docOut = path.join(thumbDocDir, `thumb_${basename}.png`);
  const staticOut = path.join(thumbStaticDir, `${basename}.png`);
  if (!fs.existsSync(sourcePath)) throw new Error(`Missing source for thumb: ${sourcePath}`);

  if (!sharp) {
    fs.copyFileSync(sourcePath, docOut);
    fs.copyFileSync(sourcePath, staticOut);
    return;
  }

  const meta = await sharp(sourcePath).metadata();
  const w = meta.width ?? 390;
  const h = meta.height ?? 844;
  const size = Math.min(w, h, 432);
  const left = Math.max(0, Math.floor((w - size) / 2));
  const top = Math.max(0, Math.floor(h * 0.18));
  const buffer = await sharp(sourcePath)
    .extract({ left, top: Math.min(top, h - size), width: size, height: size })
    .resize(144, 144)
    .modulate({ saturation: 0.8 })
    .png()
    .toBuffer();
  fs.writeFileSync(docOut, buffer);
  fs.writeFileSync(staticOut, buffer);
}
