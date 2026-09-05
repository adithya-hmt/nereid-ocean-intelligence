import { expect, test, type Page } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

async function sample(page: Page, benchmark: 'empty' | '100000') {
  await page.goto(`/?benchmark=${benchmark}`)
  const ready = page.locator('[data-render-ready="true"]')
  const complete = page.locator('[data-render-benchmark-complete="true"]')
  const fallback = page.getByText(/2D longitude\/latitude fallback/)
  await expect(ready.or(fallback)).toBeVisible({ timeout: 30_000 })
  if (await fallback.isVisible()) throw new Error(`WebGL benchmark ${benchmark} used the truthful fallback; no measurement is available.`)
  await expect(complete).toBeVisible({ timeout: 10_000 })
  return {
    points: benchmark === 'empty' ? 0 : 100000,
    initializationMs: Number((await page.locator('[data-benchmark-initialization]').textContent())?.replace(' ms', '')),
    r3fFps: Number(await page.locator('[data-benchmark-r3f-fps]').textContent()),
    browser: await page.locator('[data-benchmark-browser]').textContent(),
    hardware: await page.locator('[data-benchmark-hardware]').textContent(),
    renderer: await page.locator('[data-benchmark-renderer]').textContent(),
    probe: await page.locator('[data-benchmark-probe]').textContent(),
  }
}

test('records comparable actual-R3F empty and 100,000-point samples', async ({ page, browserName }) => {
  const emptyCanvas = await sample(page, 'empty')
  const pointCloud = await sample(page, '100000')
  const hardwareMode = process.env.NEREID_BENCHMARK_GPU === '1'
  const evidence = {
    label: 'benchmark only — synthetic rows are never scientific results',
    declared: { browser: browserName, mode: hardwareMode ? 'headed system Chromium on DISPLAY=:0 / WAYLAND_DISPLAY=wayland-1' : 'headless bundled Chromium', executable: hardwareMode ? '/usr/bin/chromium' : 'Playwright bundled Chromium', hardware: 'Browser-reported capabilities are recorded separately as measured hardware.' },
    measured: { measurement: 'R3F useFrame callbacks while the benchmark probe invalidated Canvas frameloop=demand for five seconds.', emptyCanvas, pointCloud },
  }
  await mkdir(path.resolve(process.cwd(), '../docs/evidence'), { recursive: true })
  await writeFile(path.resolve(process.cwd(), '../docs/evidence/rendering.json'), `${JSON.stringify(evidence, null, 2)}\n`)
  expect(emptyCanvas.r3fFps).toBeGreaterThan(0)
  expect(pointCloud.r3fFps).toBeGreaterThan(0)
})
