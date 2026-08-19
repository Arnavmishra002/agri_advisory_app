import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '{}',
  }));
  await page.goto('/');
  await page.waitForFunction(() => typeof window.showService === 'function');
});

test('primary desktop services open without login', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name.includes('mobile'), 'Desktop navigation contract');
  const routes = [
    ['#nav-weather', '#weather-content'],
    ['#nav-market', '#market-prices-content'],
    ['#nav-schemes', '#government-schemes-content'],
    ['#nav-ai', '#ai-assistant-content'],
  ];
  for (const [button, panel] of routes) {
    await page.locator(button).click();
    await expect(page.locator(panel)).toBeVisible();
  }
});

test('primary mobile services open without login and controls fit viewport', async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes('mobile'), 'Mobile navigation contract');
  const routes = [
    ['#bnav-weather', '#weather-content'],
    ['#bnav-market', '#market-prices-content'],
    ['#bnav-ai', '#ai-assistant-content'],
    ['#bnav-more', '#government-schemes-content'],
  ];
  for (const [button, panel] of routes) {
    const control = page.locator(button);
    await expect(control).toBeVisible();
    const box = await control.boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(412);
    await control.click();
    await expect(page.locator(panel)).toBeVisible();
  }
});
