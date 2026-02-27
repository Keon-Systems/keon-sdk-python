/**
 * Playwright configuration — ForgePilot Canonical Test Doctrine v1.0.0
 *
 * Projects:
 *  forgepilot-e2e   → tests/e2e/forgepilot/  (full user-journey E2E)
 *  site-smoke       → tests/e2e/site/         (keon.systems smoke + link integrity)
 *  component        → tests/component/         (UI unit / truthfulness / obs)
 *
 * Run targets:
 *  npx playwright test --project=forgepilot-e2e
 *  npx playwright test --project=site-smoke
 *  npx playwright test --project=component
 */

import { defineConfig, devices } from '@playwright/test'

const BASE_URL = process.env['BASE_URL'] ?? 'http://localhost:3000'
const SITE_URL = process.env['SITE_URL'] ?? 'https://keon.systems'

export default defineConfig({
  testDir: './tests',
  /* Only pick up .spec.ts files — never collide with Python tests/test_*.py */
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 2 : 0,
  workers: process.env['CI'] ? 2 : undefined,
  timeout: 30_000,
  expect: { timeout: 8_000 },

  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'playwright-report/results.json' }],
  ],

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'forgepilot-e2e',
      testDir: './tests/e2e/forgepilot',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: BASE_URL,
      },
    },
    {
      name: 'site-smoke',
      testDir: './tests/e2e/site',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: SITE_URL,
      },
    },
    {
      name: 'component',
      testDir: './tests/component',
      use: {
        ...devices['Desktop Chrome'],
        baseURL: BASE_URL,
      },
    },
  ],

  /* Start Next.js dev server for local runs against forgepilot-e2e and component */
  webServer: {
    command: 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: !process.env['CI'],
    timeout: 120_000,
    env: {
      NODE_ENV: 'test',
    },
  },
})

