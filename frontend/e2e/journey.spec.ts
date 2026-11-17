import { expect, test, type Page } from '@playwright/test'

// The demo journey: an anomaly appears, it has been investigated with evidence, experiments
// get defensible verdicts, and the data's ground truth can be revealed.

function trackFailures(page: Page): string[] {
  const failures: string[] = []
  page.on('response', (r) => {
    if (r.status() >= 400 && !r.url().endsWith('favicon.ico')) failures.push(`${r.status()} ${r.url()}`)
  })
  page.on('pageerror', (e) => failures.push(`page error: ${e.message}`))
  return failures
}

test('incident to investigation with evidence', async ({ page }) => {
  const failures = trackFailures(page)
  await page.goto('./')
  await expect(page.getByRole('heading', { name: 'Decision Center' })).toBeVisible()
  const lead = page.getByRole('link', { name: /Activation rate fell \(Platform iOS\)/ })
  await expect(lead).toContainText('1-week window')
  await lead.click()
  await expect(page.getByRole('heading', { level: 2, name: /iOS 4\.12 signups at the 'invite sent' step/ })).toBeVisible()
  await expect(page.getByText('Rule-based analysis (no LLM)')).toBeVisible()
  await page.getByRole('button', { name: /^Show evidence E-/ }).first().click()
  await expect(page.getByRole('dialog')).toContainText('Facts (what claims may cite)')
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: 'Record decision' })).toBeDisabled()
  expect(failures).toEqual([])
})

test('experiment verdicts', async ({ page }) => {
  const failures = trackFailures(page)
  await page.goto('./experiments')
  await page.getByRole('link', { name: /Aggressive upgrade prompt/ }).click()
  await expect(page.getByText("Don't ship").first()).toBeVisible()
  await expect(page.getByText(/Guardrail week-2 retention breached/)).toBeVisible()
  await page.goto('./experiments/E4')
  await expect(page.getByText('Invalid test').first()).toBeVisible()
  await expect(page.getByText(/Sample ratio mismatch/)).toBeVisible()
  await page.goto('./experiments/E1')
  await expect(page.getByText('Ship', { exact: true })).toBeVisible()
  expect(failures).toEqual([])
})

test('overview, funnels and the data page load from the snapshot', async ({ page }) => {
  const failures = trackFailures(page)
  for (const path of ['./overview', './funnels', './metrics', './investigations']) {
    await page.goto(path)
    await expect(page.locator('main h1')).toBeVisible()
    await expect(page.getByText('Could not load this data')).toHaveCount(0)
  }
  await page.goto('./data')
  await page.getByRole('button', { name: 'Reveal the scenarios' }).click()
  await expect(page.getByText(/Activation drop localized to iOS 4\.12/)).toBeVisible()
  expect(failures).toEqual([])
})
