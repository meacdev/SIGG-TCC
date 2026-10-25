import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  fullyParallel: false,
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
  webServer: [
    {
      command: `${process.env.SIGG_TEST_PYTHON || (process.platform === 'win32' ? '..\\.venv\\Scripts\\python.exe' : '../.venv/bin/python')} e2e/serve_api.py`,
      url: 'http://127.0.0.1:5001/api/v1/health/live',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev',
      url: 'http://127.0.0.1:5173',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:5001' },
      reuseExistingServer: false,
    },
  ],
});
