import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://localhost:3100', headless: true },
  webServer: { command: 'pnpm dev --port 3100', url: 'http://localhost:3100', reuseExistingServer: false },
})
