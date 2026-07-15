import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('km_location', JSON.stringify({
      name: 'Lucknow',
      state: 'Uttar Pradesh',
      lat: 26.8467,
      lon: 80.9462,
      acc: 500,
      ts: Date.now(),
    }));
  });

  await page.route('**/api/**', route => {
    const url = new URL(route.request().url());
    let body = {};

    if (url.pathname.endsWith('/market-prices/mandis/')) {
      body = {
        mandis: [{
          name: 'Lucknow Mandi',
          district: 'Lucknow',
          state: 'Uttar Pradesh',
          distance_km: 0,
          proximity: 'very_near',
          live: false,
        }],
        nearest_mandi: { name: 'Lucknow Mandi', distance_km: 0 },
        live_count: 0,
      };
    } else if (url.pathname.endsWith('/market-prices/mandi-prices/')) {
      body = {
        status: 'unavailable',
        is_live: false,
        mandi_no_live_rows: true,
        selected_mandi: 'Lucknow Mandi',
        message: "No current official arrival rows for 'Lucknow Mandi'.",
        top_crops: [],
      };
    } else if (url.pathname.endsWith('/market-prices/')) {
      body = {
        status: 'success',
        is_live: true,
        state: 'Uttar Pradesh',
        coverage: 'state',
        data_source: 'Agmarknet 2.0 API',
        top_crops: [{
          crop_name: 'Wheat',
          crop_name_hindi: 'गेहूँ',
          modal_price: 2540,
          is_live: true,
          price_source: 'agmarknet_state_average',
          mandi_name: 'Uttar Pradesh Agmarknet average',
          date: '13-07-2026',
        }],
      };
    }

    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });

  await page.goto('/');
  await page.waitForFunction(() => typeof window.showService === 'function');
});

test('exact mandi absence finishes loading and preserves separate state benchmark', async ({ page }) => {
  await page.locator('#nav-market').click();
  await expect(page.locator('#mandiSelector')).toContainText('Lucknow Mandi');

  await page.locator('#mandiSelector').selectOption('Lucknow Mandi');
  await expect(page.locator('#mandiStatusBadge')).toContainText('अभी ताजा आधिकारिक आवक नहीं मिली');
  await expect(page.locator('#marketLiveBanner')).toContainText('कोई दूसरी मंडी का भाव इसके नाम पर नहीं दिखाया गया है');

  const stateButton = page.locator('.show-state-market-prices');
  await expect(stateButton).toBeVisible();
  await stateButton.click();

  await expect(page.locator('#mandiStatusBadge')).toContainText('नवीनतम आधिकारिक औसत भाव');
  await expect(page.locator('#pricesData')).toContainText('₹2,540');
  await expect(page.locator('#mandiSelector')).toHaveValue('');
});
