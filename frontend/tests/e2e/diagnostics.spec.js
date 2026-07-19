import { expect, test } from '@playwright/test';

const advisoryResponse = {
  status: 'advisory_fallback',
  crop_display: 'Tomato',
  location: 'Unnao, Uttar Pradesh',
  timestamp: '2026-07-14T06:00:00Z',
  message: 'फोटो मिला। सत्यापित classifier उपलब्ध नहीं है, इसलिए लक्षण-आधारित सलाह दिखाई जा रही है।',
  diagnosis: [],
};

async function openDiagnostics(page) {
  await page.goto('/');
  await page.waitForFunction(() => typeof window.runKrishiRakshaDiagnosis === 'function');
  await page.evaluate(() => window.showService('pest-control'));
  await page.locator('#krCropSearchInput').fill('Tomato');
  await page.evaluate(() => {
    document.getElementById('krCropValue').value = 'tomato';
  });
  await page.locator('#imgCloseUp').setInputFiles({
    name: 'tomato-leaf.png',
    mimeType: 'image/png',
    buffer: Buffer.from('89504e470d0a1a0a', 'hex'),
  });
}

test('guest receives honest advisory fallback and cannot submit owned feedback', async ({ page }) => {
  let diagnosticBody;
  await page.route('**/api/diagnostics/detect/', async route => {
    diagnosticBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(advisoryResponse),
    });
  });
  await openDiagnostics(page);
  await page.locator('#diagnosisRunBtn').click();

  await expect(page.locator('#krishiRakshaResults')).toContainText('classifier उपलब्ध नहीं');
  await expect(page.locator('#krishiRakshaResults')).toContainText('feedback देने के लिए लॉगिन');
  expect(diagnosticBody.session_id).toMatch(/^diag-/);
  expect(diagnosticBody.session_id).not.toContain('sess_');
});

test('authenticated diagnosis and feedback use the same owned request ID', async ({ page }) => {
  let diagnosticBody;
  let diagnosticAuth;
  let feedbackBody;
  let feedbackAuth;
  await page.route('**/api/diagnostics/detect/', async route => {
    diagnosticBody = route.request().postDataJSON();
    diagnosticAuth = route.request().headers().authorization;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(advisoryResponse),
    });
  });
  await page.route('**/api/diagnostics/feedback/', async route => {
    feedbackBody = route.request().postDataJSON();
    feedbackAuth = route.request().headers().authorization;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{"status":"success"}',
    });
  });
  await openDiagnostics(page);
  await page.evaluate(() => window.KM_Auth._onLoginSuccess({
    access: 'owned-access',
    refresh: 'owned-refresh',
    user: { id: 11, username: 'owner', name: 'Owner Farmer' },
  }));
  await page.locator('#diagnosisRunBtn').click();
  const usefulFeedbackButton = page.getByRole('button', { name: /हाँ, उपयोगी/ });
  await expect(usefulFeedbackButton).toBeVisible();
  const feedbackRequest = page.waitForRequest(request => {
    const url = new URL(request.url());
    return url.pathname.endsWith('/api/diagnostics/feedback/');
  });
  await usefulFeedbackButton.click({ force: true });
  await feedbackRequest;

  expect(diagnosticAuth).toBe('Bearer owned-access');
  expect(feedbackAuth).toBe('Bearer owned-access');
  expect(feedbackBody.session_id).toBe(diagnosticBody.session_id);
  expect(feedbackBody.is_correct).toBe(true);
});
