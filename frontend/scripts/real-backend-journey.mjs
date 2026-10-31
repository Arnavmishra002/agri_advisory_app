import { chromium, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { readFile, mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';

const api = process.env.KM_TEST_API_URL;
assert.match(api || '', /^http:\/\/(localhost|127\.0\.0\.1):\d+$/);
assert.ok(process.env.KM_TEST_OTP_CAPTURE, 'Run through Django browser_journeys only');
// Fail closed when the actual backend is unavailable; never substitute API responses.
assert.equal((await fetch(`${api}/api/health/`)).status, 200);
const vite = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '4197', '--strictPort'], {
  env: { ...process.env, VITE_API_BASE_URL: api }, stdio: ['ignore', 'pipe', 'pipe'],
});
let logs = '';
vite.stdout.on('data', x => { logs += x; });
vite.stderr.on('data', x => { logs += x; });
let browser;
try {
  await expect.poll(async () => {
    try { return (await fetch('http://127.0.0.1:4197')).status; } catch { return 0; }
  }, { timeout: 15000 }).toBe(200);
  browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  await page.addInitScript(() => { localStorage.setItem('km_lang', 'en'); localStorage.setItem('km_theme', 'light'); });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:4197');
  await page.locator('#navLoginBtn').click();
  await page.locator('#authPhoneInput').fill('9000000099');
  await page.locator('#btnSendOtp').click();
  await expect(page.locator('#otpStep2')).toBeVisible();
  const otp = (await readFile(process.env.KM_TEST_OTP_CAPTURE, 'utf8')).trim();
  for (let i = 0; i < 6; i++) await page.locator('.otp-digit').nth(i).fill(otp[i]);
  await expect(page.locator('#navUserPill')).toBeVisible();
  await expect(page.locator('#authModal')).toBeHidden();
  await page.locator('#nav-ai').click();
  await page.locator('#fp_crop').fill('wheat');
  const saved = page.waitForResponse(r => r.url().endsWith('/api/farmer-profile/') && r.request().method() === 'POST');
  await page.locator('#fp_crop').press('Tab');
  assert.ok((await saved).ok(), 'Profile save must reach and succeed on Django');
  await expect(page.locator('#profileSaveIndicator')).toContainText('Saved');
  const token = await page.evaluate(() => localStorage.getItem('km_access_token'));
  const profile = await page.request.get(`${api}/api/farmer-profile/me/`, { headers: { Authorization: `Bearer ${token}` } });
  assert.equal((await profile.json()).profile.current_crop, 'wheat');
  const refresh = await page.evaluate(() => sessionStorage.getItem('km_refresh_token'));
  assert.equal(await page.evaluate(() => localStorage.getItem('km_refresh_token')), null);
  const refreshed = await page.request.post(`${api}/api/token/refresh/`, { data: { refresh } });
  assert.equal(refreshed.status(), 200);
  await page.reload();
  await expect(page.locator('#navUserPill')).toBeVisible();
  await page.locator('#nav-ai').click();
  await expect(page.locator('#fp_crop')).toHaveValue('wheat');
  await page.locator('.navbar-user-dropdown-btn').click();
  await page.locator('[onclick*="KM_Auth.logout"]').click();
  await expect(page.locator('#navLoginBtn')).toBeVisible();
  await expect(page.locator('#fp_crop')).toHaveValue('');
  assert.equal(await page.evaluate(() => localStorage.getItem('km_access_token')), null);
  const reused = await page.request.post(`${api}/api/users/otp/verify/`, { data: { phone_number: '9000000099', otp_code: otp } });
  assert.notEqual(reused.status(), 200);
  assert.equal((await page.request.get(`${api}/api/farmer-profile/me/`)).status(), 401);
  await mkdir('../audit/remediation/real-backend', { recursive: true });
  await page.screenshot({ path: '../audit/remediation/real-backend/logout.png', fullPage: true, animations: 'disabled' });
  assert.deepEqual(errors, []);
  console.log('PASS: real Django OTP/JWT/profile persistence/refresh/logout/reuse; SMS boundary simulated');
} finally {
  if (browser) await browser.close();
  vite.kill('SIGTERM');
  await new Promise(resolve => vite.once('exit', resolve));
}
