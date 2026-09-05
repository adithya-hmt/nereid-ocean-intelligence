import { expect, test } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

test('records the 100,000-point benchmark separately from scientific results', async ({ page, browserName }) => {
  await page.goto('/?benchmark=100000')
  const ready = page.locator('[data-render-ready="true"]')
  const complete = page.locator('[data-render-benchmark-complete="true"]')
  const fallback = page.getByText(/2D longitude\/latitude fallback/)
  await expect(ready.or(fallback)).toBeVisible({ timeout: 30_000 })
  if (await fallback.isVisible()) {
    const blocked = { label: 'benchmark only — synthetic rows are never scientific results', points: 100000, status: 'blocked', blocker: 'The Playwright browser could not initialize WebGL and displayed the truthful 2D fallback. No FPS or initialization measurement was recorded.' }
    await mkdir(path.resolve(process.cwd(), '../docs/evidence'), { recursive: true })
    await writeFile(path.resolve(process.cwd(), '../docs/evidence/rendering.json'), `${JSON.stringify(blocked, null, 2)}\n`)
    throw new Error(blocked.blocker)
  }
  await expect(complete).toBeVisible({ timeout: 10_000 })
  const initializationMs = Number((await page.locator('[data-benchmark-initialization]').textContent())?.replace(' ms', ''))
  const r3fFps = Number(await page.locator('[data-benchmark-r3f-fps]').textContent())
  const browser = await page.locator('[data-benchmark-browser]').textContent()
  const hardware = await page.locator('[data-benchmark-hardware]').textContent()
  const evidence = {
    label: 'benchmark only — synthetic rows are never scientific results',
    points: 100000,
    declared: { browser: browserName, hardware: 'Playwright benchmark runner; browser-reported capabilities are displayed separately as measured hardware.' },
    measured: { initializationMs, r3fFps, browser, hardware, measurement: 'R3F useFrame callbacks while the benchmark probe invalidated Canvas frameloop=demand for five seconds.' },
  }
  await mkdir(path.resolve(process.cwd(), '../docs/evidence'), { recursive: true })
  await writeFile(path.resolve(process.cwd(), '../docs/evidence/rendering.json'), `${JSON.stringify(evidence, null, 2)}\n`)
  expect(initializationMs).toBeGreaterThan(0)
  expect(r3fFps).toBeGreaterThan(0)
})
