import { expect, test } from '@playwright/test'
import { inflateRawSync } from 'node:zlib'

const expectedMembers = ['README.txt', 'selection.csv', 'provenance.json', 'query-plan.json', 'methods.json']

function unzip(bytes: Buffer) {
  const members = new Map<string, Buffer>()
  let offset = 0
  while (bytes.readUInt32LE(offset) === 0x04034b50) {
    const flags = bytes.readUInt16LE(offset + 6)
    const method = bytes.readUInt16LE(offset + 8)
    const compressedSize = bytes.readUInt32LE(offset + 18)
    const nameLength = bytes.readUInt16LE(offset + 26)
    const extraLength = bytes.readUInt16LE(offset + 28)
    expect(flags & 0x08).toBe(0)
    const nameStart = offset + 30
    const name = bytes.subarray(nameStart, nameStart + nameLength).toString('utf8')
    const dataStart = nameStart + nameLength + extraLength
    const compressed = bytes.subarray(dataStart, dataStart + compressedSize)
    members.set(name, method === 8 ? inflateRawSync(compressed) : compressed)
    offset = dataStart + compressedSize
  }
  return members
}

function selectedIdentities(csv: string) {
  const [header, ...lines] = csv.trim().split('\n')
  const fields = header.split(',').map((field) => field.trim())
  const index = (name: string) => fields.indexOf(name)
  return new Set(lines.map((line) => {
    const values = line.split(',').map((value) => value.trim())
    return `${values[index('wmo')]}/${values[index('cycle')]}/${values[index('source_profile_index')]}`
  }))
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
  const trajectory = await page.locator('.trajectory-readout').last().textContent()
  const readout = /Longitude (-?\d+(?:\.\d+)?)° to (-?\d+(?:\.\d+)?)°; latitude (-?\d+(?:\.\d+)?)° to (-?\d+(?:\.\d+)?)°; depth (-?\d+(?:\.\d+)?) to (-?\d+(?:\.\d+)?) m; time cutoff: ([^;]+); rendered ([\d,]+) of ([\d,]+) points; vertical exaggeration (\d+)×\./.exec(trajectory ?? '')
  expect(readout).not.toBeNull()
  const [, longitudeMin, longitudeMax, latitudeMin, latitudeMax, depthMin, depthMax, cutoff, rendered, total, exaggeration] = readout!
  for (const value of [longitudeMin, longitudeMax, latitudeMin, latitudeMax, depthMin, depthMax, exaggeration]) expect(Number.isFinite(Number(value))).toBeTruthy()
  expect(Number(longitudeMin)).toBeLessThanOrEqual(Number(longitudeMax))
  expect(Number(latitudeMin)).toBeLessThanOrEqual(Number(latitudeMax))
  expect(Number(depthMin)).toBeLessThanOrEqual(Number(depthMax))
  expect(Number(rendered.replaceAll(',', ''))).toBeGreaterThan(0)
  expect(Number(total.replaceAll(',', ''))).toBeGreaterThanOrEqual(Number(rendered.replaceAll(',', '')))
  expect(Number(exaggeration)).toBeGreaterThanOrEqual(0)
  expect(Number.isNaN(Date.parse(cutoff))).toBeFalsy()
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
  const members = unzip(Buffer.concat(chunks))
  expect(Array.from(members.keys())).toEqual(expectedMembers)
  expect(selectedIdentities(members.get('selection.csv')!.toString('utf8'))).toEqual(new Set(['1902202/161/0', '2902388/274/0']))
  expect(selectedIdentities(members.get('selection.csv')!.toString('utf8')).has('2902388/274/1')).toBeFalsy()
  expect(file.suggestedFilename()).toBe('nereid-evidence.zip')
  expect(JSON.parse(exportBody).selections).toHaveLength(2)
  expect(outbound).toEqual([])
})
