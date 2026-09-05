import { defineConfig } from '@playwright/test'

const hardwareBenchmark = process.env.NEREID_BENCHMARK_GPU === '1'

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:3100',
    launchOptions: hardwareBenchmark ? { headless: false, executablePath: '/usr/bin/chromium' } : { headless: true },
  },
  webServer: { command: 'pnpm dev --port 3100', url: 'http://localhost:3100', reuseExistingServer: false },
})
