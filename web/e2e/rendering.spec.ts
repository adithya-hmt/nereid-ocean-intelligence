import { expect, test } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

test('records the 100,000-point benchmark separately from scientific results', async ({ page, browserName }) => {
  const started = performance.now()
  await page.goto('/?benchmark=100000')
  const ready = page.locator('[data-render-ready="true"]')
  const fallback = page.getByText(/2D longitude\/latitude fallback/)
  await expect(ready.or(fallback)).toBeVisible({ timeout: 30_000 })
  if (await fallback.isVisible()) {
    const blocked = { label: 'benchmark only — synthetic rows are never scientific results', points: 100000, status: 'blocked', blocker: 'The Playwright browser could not initialize WebGL and displayed the truthful 2D fallback. No FPS or initialization measurement was recorded.' }
    await mkdir(path.resolve(process.cwd(), '../docs/evidence'), { recursive: true })
    await writeFile(path.resolve(process.cwd(), '../docs/evidence/rendering.json'), `${JSON.stringify(blocked, null, 2)}\n`)
    throw new Error(blocked.blocker)
  }
  const initializationMs = performance.now() - started
  const sample = await page.evaluate(async () => {
    const start = performance.now()
    let frames = 0
    await new Promise<void>((resolve) => {
      const frame = () => {
        frames += 1
        if (performance.now() - start >= 5000) resolve()
        else requestAnimationFrame(frame)
      }
      requestAnimationFrame(frame)
    })
    return {
      fps: frames / ((performance.now() - start) / 1000),
      browser: navigator.userAgent,
      hardware: { hardwareConcurrency: navigator.hardwareConcurrency, deviceMemory: (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? null },
    }
  })
  const evidence = {
    label: 'benchmark only — synthetic rows are never scientific results',
    points: 100000,
    declared: { browser: browserName, hardware: 'Playwright-managed browser environment; hardware values reported by navigator.' },
    measured: { initializationMs, fps: sample.fps, browser: sample.browser, hardware: sample.hardware },
  }
  await mkdir(path.resolve(process.cwd(), '../docs/evidence'), { recursive: true })
  await writeFile(path.resolve(process.cwd(), '../docs/evidence/rendering.json'), `${JSON.stringify(evidence, null, 2)}\n`)
  expect(sample.fps).toBeGreaterThanOrEqual(30)
})
