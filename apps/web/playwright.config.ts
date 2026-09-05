import { defineConfig, devices } from '@playwright/test';

const useProductionServer = process.env.PLAYWRIGHT_WEB_SERVER === 'production';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: useProductionServer
      ? 'pnpm build && node build'
      : 'pnpm dev --host 127.0.0.1 --port 4173',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: !process.env.CI,
    timeout: useProductionServer ? 180_000 : 120_000,
    env: {
      ...process.env,
      HOST: '127.0.0.1',
      PORT: '4173',
      ORIGIN: 'http://127.0.0.1:4173',
      VITE_API_BASE_URL: process.env.VITE_API_BASE_URL ?? '/api/v1',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
