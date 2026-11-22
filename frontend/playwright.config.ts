import { defineConfig, devices } from '@playwright/test';

const frontendPort = 3100;
const backendPort = 4010;

export default defineConfig({
  testDir: './tests/e2e',
  outputDir: 'test-results/playwright',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI
    ? [['line'], ['html', { outputFolder: 'playwright-report', open: 'never' }]]
    : [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: `http://127.0.0.1:${frontendPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    colorScheme: 'light',
  },
  projects: [
    {
      name: 'desktop-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'mobile-chromium',
      use: { ...devices['Pixel 5'], viewport: { width: 390, height: 844 } },
    },
    {
      name: 'tablet-portrait-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 768, height: 1024 } },
    },
    {
      name: 'tablet-landscape-chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1024, height: 768 } },
    },
    {
      name: 'dark-desktop-chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        colorScheme: 'dark',
      },
    },
  ],
  webServer: [
    {
      command: `node tests/e2e/support/mock-backend.mjs ${backendPort}`,
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: `pnpm exec next dev --hostname 127.0.0.1 --port ${frontendPort}`,
      url: `http://127.0.0.1:${frontendPort}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        BACKEND_URL: `http://127.0.0.1:${backendPort}`,
        NEXT_PUBLIC_BASE_URL: `http://127.0.0.1:${frontendPort}`,
        AUTH_SECRET: 'browser-test-auth-secret-that-is-at-least-32-characters',
        GH_CLIENT_ID: 'browser-test-github-client-id',
        GH_CLIENT_SECRET: 'browser-test-github-client-secret',
        GOOGLE_CLIENT_ID: 'browser-test-google-client-id',
        GOOGLE_CLIENT_SECRET: 'browser-test-google-client-secret',
        MCP_PUBLIC_URL: `http://127.0.0.1:${backendPort}/mcp`,
      },
    },
  ],
});
