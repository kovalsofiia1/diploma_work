import { defineConfig } from '@playwright/test';
import { resolve } from 'node:path';

const frontendDirectory = __dirname;
const backendDirectory = resolve(frontendDirectory, '..', 'backend');

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:18101',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 18001',
      cwd: backendDirectory,
      url: 'http://127.0.0.1:18001/health',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command:
        'npx ng serve --host 127.0.0.1 --port 18101 --proxy-config proxy.conf.e2e.json --allowed-hosts all',
      cwd: frontendDirectory,
      url: 'http://127.0.0.1:18101',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
