import { defineConfig } from '@playwright/test';

export default defineConfig({
  timeout: 120000,
  use: {
    channel: 'chrome',
    headless: false,
    viewport: { width: 1280, height: 800 },
    ignoreHTTPSErrors: true,
  },
});
