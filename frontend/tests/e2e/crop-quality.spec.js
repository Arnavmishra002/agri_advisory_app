import { expect, test } from '@playwright/test';

for (const hasCoverageBasis of [true, false]) {
test(`crop quality labels use verified semantics (basis=${hasCoverageBasis})`, async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('km_location', JSON.stringify({
      name: 'Lucknow', state: 'Uttar Pradesh', lat: 26.8467, lon: 80.9462,
      acc: 500, ts: Date.now(),
    }));
  });
  await page.route('**/api/**', route => {
    const isCrops = new URL(route.request().url()).pathname === '/api/advisories/';
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(isCrops ? {
      weather_is_live: true, weather_data_source: 'MET Norway',
      weather_snapshot: { temperature: 26, humidity: null },
      input_provenance: { soil_type: 'regional_assumption' },
      recommendations: [{
        crop_name: 'Wheat', crop_name_local: 'Wheat', suitability_score: 60,
        profit_per_hectare: null, input_cost_per_hectare: 25000,
        prediction_data: { data_completeness: 0.1, data_completeness_basis: hasCoverageBasis ? 'farmer_inputs_and_live_sources_v1' : undefined },
      }],
    } : {}) });
  });
  await page.goto('/');
  await page.waitForFunction(() => typeof window.showService === 'function');
  await page.evaluate(() => window.showService('crop-recommendations'));
  const result = page.locator('#cropsData');
  await expect(result).toContainText('Wheat');
  if (hasCoverageBasis) await expect(result).toContainText('10%');
  else await expect(result).not.toContainText('10%');
  await expect(result).toContainText(/regional assumptions|क्षेत्रीय अनुमान/);
  await expect(result).toContainText('MET Norway');
  await expect(result).not.toContainText('null%');
  await expect(result).not.toContainText('undefined');
  await expect(result).not.toContainText('Open-Meteo · Real-time');
});
}
