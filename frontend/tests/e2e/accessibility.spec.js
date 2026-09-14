import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({ contentType: 'application/json', body: '{}' }));
  await page.addInitScript(() => localStorage.setItem('km_lang', 'en'));
  await page.goto('/');
});

test('main landmark, skip link, labelled controls and modal keyboard restoration', async ({ page, browserName }) => {
  await expect(page.getByRole('main')).toHaveCount(1);
  await page.keyboard.press(browserName === 'webkit' ? 'Alt+Tab' : 'Tab');
  await expect(page.locator('.skip-link')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#mainContent')).toBeFocused();
  if (!await page.locator('#languageSwitcher').isVisible()) await page.locator('.navbar-toggler').click();
  await expect(page.locator('#languageSwitcher')).toHaveAccessibleName(/Language/i);
  await expect(page.locator('#locationSearchInput')).toHaveAccessibleName(/village|district/i);
  await page.locator('#navLoginBtn').click();
  await expect(page.locator('#authModal')).toBeVisible();
  await expect(page.locator('#authModal')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.locator('#authModal')).toBeHidden();
  await expect(page.locator('#navLoginBtn')).toBeFocused();
  expect(await page.locator('#navLoginBtn').evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
});

for (const width of [320, 360, 768, 1440]) {
  test(`all public panels fit at ${width}px with RTL and long translations`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const language of ['en', 'ur']) {
      await expect(page.locator('#navbarNav')).not.toHaveClass(/collapsing/);
      if (!await page.locator('#languageSwitcher').isVisible()) await page.locator('.navbar-toggler').click();
      await expect(page.locator('#languageSwitcher')).toBeVisible();
      await page.locator('#languageSwitcher').selectOption(language);
      await expect(page.locator('html')).toHaveAttribute('dir', language === 'ur' ? 'rtl' : 'ltr');
      for (const panel of ['home', 'weather', 'market-prices', 'crop-recommendations', 'pest-control', 'government-schemes', 'ai-assistant', 'field-advisory']) {
        await page.evaluate(name => window.showService(name), panel);
        await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - innerWidth), { message: panel }).toBeLessThanOrEqual(1);
      }
    }
    await page.reload();
    // addInitScript intentionally resets this test to English on reload.
    await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
  });
}
