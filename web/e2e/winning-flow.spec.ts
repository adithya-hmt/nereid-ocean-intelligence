import { expect, test } from '@playwright/test'

const expectedMembers = ['README.txt', 'selection.csv', 'provenance.json', 'query-plan.json', 'methods.json']

function zipContainsMembers(bytes: Uint8Array) {
  const text = new TextDecoder().decode(bytes)
  return expectedMembers.every((name) => text.includes(name))
}

test('replays the committed real March snapshot without outbound network access', async ({ page }) => {
  const outbound: string[] = []
  await page.route('**/*', async (route) => {
    const url = new URL(route.request().url())
    if (url.hostname === 'localhost' || url.hostname === '127.0.0.1' || url.hostname === '::1') return route.continue()
    outbound.push(url.href)
    await route.abort('blockedbyclient')
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Use March 2023 example' }).click()
  await page.getByRole('button', { name: 'Run investigation' }).click()
  await expect(page.getByRole('heading', { name: 'Native profile observations' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Scientific receipt' })).toBeVisible()
  await page.getByLabel(/2902388 \/ cycle 274 \/ representation 1/).uncheck()
  await expect(page.locator('input[type="checkbox"]:checked')).toHaveCount(2)
  await expect(page.locator('.trajectory-readout').last()).toContainText(/Longitude .*latitude .*depth .*time cutoff: .*rendered .* of .*points; vertical exaggeration/)
  await expect(page.getByText(/1902202 \/ cycle 161/).first()).toBeVisible()
  await expect(page.getByText(/2902388 \/ cycle 274/).first()).toBeVisible()
  await expect(page.getByText('DOI https://doi.org/10.17882/42182').first()).toBeVisible()
  await expect(page.getByText(/source_representations/)).toBeVisible()
  await expect(page.getByText(/multiple ARGO vertical sampling schemes/)).toBeVisible()
  await expect(page.getByText(/test-only|synthetic fallback/i)).toHaveCount(0)

  let exportBody = ''
  page.on('request', (request) => { if (request.url().endsWith('/v1/export')) exportBody = request.postData() ?? '' })
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download evidence ZIP' }).click()
  const file = await download
  const stream = await file.createReadStream()
  const chunks: Buffer[] = []
  for await (const chunk of stream) chunks.push(Buffer.from(chunk))
  const contents = Buffer.concat(chunks)
  expect(zipContainsMembers(contents)).toBeTruthy()
  expect(file.suggestedFilename()).toBe('nereid-evidence.zip')
  expect(JSON.parse(exportBody).selections).toHaveLength(2)
  expect(outbound).toEqual([])
})
