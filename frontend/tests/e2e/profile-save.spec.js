import { expect, test } from '@playwright/test';

for (const logout of [false, true]) {
test(`profile saves are serialized (logout before queued save: ${logout})`, async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('km_access_token', 'profile-test-access');
    localStorage.setItem('km_user', JSON.stringify({ id: 7, username: 'fixture_farmer' }));
  });
  const bodies = [];
  let releaseFirst;
  await page.route('**/api/**', async route => {
    if (new URL(route.request().url()).pathname === '/api/farmer-profile/' && route.request().method() === 'POST') {
      bodies.push(route.request().postDataJSON());
      if (bodies.length === 1) await new Promise(resolve => { releaseFirst = resolve; });
      return route.fulfill({ json: { profile: bodies.at(-1) } });
    }
    return route.fulfill({ json: { profile: {} } });
  });
  await page.goto('/');
  await page.waitForFunction(() => Boolean(window._upsertFarmerProfile && KM_Auth.isLoggedIn()));
  await page.evaluate(() => {
    window.firstSave = _upsertFarmerProfile({ current_crop: 'wheat' });
    window.secondSave = _upsertFarmerProfile({ current_crop: 'rice' });
  });
  await expect.poll(() => bodies.length).toBe(1);
  // A browser event-loop barrier ensures the second edit has been scheduled.
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
  expect(bodies).toHaveLength(1);
  if (logout) await page.evaluate(() => KM_Auth.logout());
  releaseFirst();
  await page.evaluate(() => Promise.all([window.firstSave, window.secondSave]));
  expect(bodies.map(body => body.current_crop)).toEqual(logout ? ['wheat'] : ['wheat', 'rice']);
});
}
