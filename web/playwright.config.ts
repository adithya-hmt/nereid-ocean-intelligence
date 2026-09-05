import { defineConfig } from '@playwright/test'

const hardwareBenchmark = process.env.NEREID_BENCHMARK_GPU === '1'

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:3100',
    launchOptions: hardwareBenchmark ? { headless: false, executablePath: '/usr/bin/chromium' } : { headless: true },
  },
  webServer: {
    command: "sh -c 'NEREID_SNAPSHOT_DIR=../data/snapshots/indian-ocean-2023-03 NEREID_WEB_ORIGIN=http://localhost:3100 uv run --project ../api uvicorn nereid_api.main:create_offline_app --factory --host 127.0.0.1 --port 8000 --app-dir ../api/src & api=$!; trap \"kill $api\" EXIT; NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 pnpm dev --port 3100'",
    url: 'http://localhost:3100',
    reuseExistingServer: false,
  },
})
