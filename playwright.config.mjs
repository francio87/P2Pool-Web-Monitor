import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: 'ui.spec.mjs',
  fullyParallel: false,
  reporter: 'list',
  use: {
    browserName: 'chromium',
    headless: true,
    viewport: { width: 1440, height: 1000 },
  },
});
