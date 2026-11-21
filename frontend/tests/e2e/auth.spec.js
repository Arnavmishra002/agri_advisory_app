import { expect, test } from '@playwright/test';

test('OTP request timeout preserves phone and never enters code step', async ({ page }) => {
  await page.clock.install();
  await page.route('**/api/**', route => {
    if (route.request().url().includes('/otp/request/')) return;
    return route.fulfill({ contentType: 'application/json', body: '{}' });
  });
  await page.goto('/');
  await page.locator('#navLoginBtn').click();
  await page.locator('#authPhoneInput').fill('9000000099');
  await page.locator('#btnSendOtp').click();
  await page.clock.fastForward(16000);
  await expect(page.locator('#btnSendOtp')).toBeEnabled();
  await expect(page.locator('#otpStep2')).toBeHidden();
  await expect(page.locator('#authPhoneInput')).toHaveValue('9000000099');
});

const user = {
  id: 7,
  username: 'beta_farmer',
  name: 'Beta Farmer',
  phone: '9876543210',
};

async function preparePage(page) {
  await page.addInitScript(() => {
    localStorage.clear();
    sessionStorage.clear();
    window.__authEvents = [];
    window.addEventListener('km:auth-changed', event => {
      window.__authEvents.push(event.detail);
    });
  });
  await page.goto('/');
  await page.waitForFunction(() => Boolean(window.KM_Auth));
}

async function openAuth(page, tab) {
  await page.evaluate(value => window.KM_Auth.openModal(value), tab);
  await expect(page.locator('#authModal')).toBeVisible();
}

test('registration migrates signed guest state and logout clears all auth fields', async ({ page }) => {
  await preparePage(page);
  await page.evaluate(() => {
    sessionStorage.setItem('km_guest_session_token', 'signed-guest-token');
    localStorage.setItem('km_selected_location', JSON.stringify({ name: 'Unnao', confirmed: true }));
  });

  let registrationBody;
  await page.route('**/api/users/register/', async route => {
    registrationBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access: 'access-one',
        refresh: 'refresh-one',
        user,
        guest_session_migrated: true,
      }),
    });
  });
  await page.route('**/api/users/logout/', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '{"success":true}',
  }));

  await openAuth(page, 'register');
  await page.locator('#regNameInput').fill('Beta Farmer');
  await page.locator('#regUsernameInput').fill('beta_farmer');
  await page.locator('#regPasswordInput').fill('strong-pass-123');
  await page.locator('#regStateInput').fill('Uttar Pradesh');
  await page.locator('#btnRegister').click();

  await expect(page.locator('#navUserName')).toHaveText('Beta Farmer');
  expect(registrationBody.guest_session_token).toBe('signed-guest-token');
  expect(registrationBody.phone_number).toBeUndefined();
  expect(registrationBody.session_id).toBeTruthy();
  expect(await page.evaluate(() => localStorage.getItem('km_access_token'))).toBe('access-one');
  expect(await page.evaluate(() => sessionStorage.getItem('km_refresh_token'))).toBe('refresh-one');
  expect(await page.evaluate(() => localStorage.getItem('km_refresh_token'))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('km_selected_location'))).toContain('Unnao');
  expect(await page.evaluate(() => window.__authEvents.at(-1))).toMatchObject({
    guestSessionMigrated: true,
  });

  await page.evaluate(() => window.KM_Auth.logout());
  await expect(page.locator('#navLoginBtn')).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('km_access_token'))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('km_user'))).toBeNull();
  expect(await page.evaluate(() => sessionStorage.getItem('km_refresh_token'))).toBeNull();

  await openAuth(page, 'register');
  for (const selector of [
    '#regNameInput', '#regUsernameInput', '#regPasswordInput',
    '#regStateInput',
  ]) {
    await expect(page.locator(selector)).toHaveValue('');
  }
});

test('password login accepts email and refresh keeps the rotated refresh token', async ({ page }) => {
  await preparePage(page);
  let loginBody;
  await page.route('**/api/token/', async route => {
    loginBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{"access":"old-access","refresh":"session-refresh"}',
    });
  });
  await page.route('**/api/users/me/', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(user),
  }));
  await page.route('**/api/token/refresh/', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '{"access":"new-access","refresh":"rotated-refresh"}',
  }));

  await openAuth(page, 'password');
  await page.locator('#authUsernameInput').fill('farmer@example.com');
  await page.locator('#authPasswordInput').fill('strong-pass-123');
  await page.locator('#btnLoginPassword').click();
  await expect(page.locator('#navUserName')).toHaveText('Beta Farmer');
  expect(loginBody).toEqual({ username: 'farmer@example.com', password: 'strong-pass-123' });

  await page.evaluate(() => window.KM_Auth.refreshToken());
  await expect.poll(() => page.evaluate(() => localStorage.getItem('km_access_token')))
    .toBe('new-access');
  expect(await page.evaluate(() => sessionStorage.getItem('km_refresh_token')))
    .toBe('rotated-refresh');
});

test('expired OTP stays logged out and shows a farmer-safe error', async ({ page }) => {
  await preparePage(page);
  await page.evaluate(() => window.setLanguage('hi'));
  await page.route('**/api/users/otp/request/', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '{"success":true,"sms_sent":true,"delivery_status":"accepted"}',
  }));
  await page.route('**/api/users/otp/verify/', route => route.fulfill({
    status: 400,
    contentType: 'application/json',
    body: '{"error":"OTP expired","error_hi":"OTP समाप्त हो गया है। नया OTP मंगाएं।"}',
  }));

  await openAuth(page, 'phone');
  await page.locator('#authPhoneInput').fill('9876543210');
  await page.locator('#btnSendOtp').click();
  await expect(page.locator('#otpStep2')).toBeVisible();
  const digits = page.locator('#otpInputGroup .otp-digit');
  for (let index = 0; index < 6; index += 1) {
    await digits.nth(index).fill(String(index + 1));
  }
  await expect(page.locator('#otpVerifyError')).toContainText('OTP समाप्त हो गया');
  expect(await page.evaluate(() => window.KM_Auth.isLoggedIn())).toBe(false);
});

test('ISSUE-02: an unsent SMS never opens code entry or starts countdown', async ({ page }) => {
  await preparePage(page);
  await page.route('**/api/users/otp/request/', route => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ success: true, sms_sent: false }),
  }));
  await openAuth(page, 'phone');
  await page.locator('#authPhoneInput').fill('9876543210');
  await page.locator('#btnSendOtp').click();
  await expect(page.locator('#otpPhoneError')).toBeVisible();
  await expect(page.locator('#otpStep2')).toBeHidden();
  expect(await page.evaluate(() => window.KM_Auth._countdownTimer)).toBeNull();
  await expect(page.locator('#authPhoneInput')).toHaveValue('9876543210');
});

// Real base64url JWTs: the token-timing logic reads iat/exp, so opaque test
// strings would skip it entirely.
function jwt(claims) {
  const b64 = value => Buffer.from(JSON.stringify(value)).toString('base64url');
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64(claims)}.signature`;
}

const DEVICE_NOW = Date.UTC(2026, 9, 31, 9, 0, 0);
const SERVER_SKEW_S = 5 * 3600; // the phone's clock runs 5 h ahead of the server

function serverToken(serial) {
  const iat = Math.floor(DEVICE_NOW / 1000) - SERVER_SKEW_S + serial * 1800;
  return jwt({ token_type: 'access', iat, exp: iat + 1800, user_id: 7 });
}

test('refresh follows the token lifetime even when the phone clock is hours off', async ({ page }) => {
  await page.clock.install({ time: DEVICE_NOW });
  await preparePage(page);
  await page.route('**/api/token/', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ access: serverToken(0), refresh: 'refresh-0' }),
  }));
  await page.route('**/api/users/me/', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(user),
  }));
  const refreshBodies = [];
  await page.route('**/api/token/refresh/', async route => {
    refreshBodies.push(route.request().postDataJSON());
    const n = refreshBodies.length;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access: serverToken(n), refresh: `refresh-${n}` }),
    });
  });

  await openAuth(page, 'password');
  await page.locator('#authUsernameInput').fill('farmer@example.com');
  await page.locator('#authPasswordInput').fill('strong-pass-123');
  await page.locator('#btnLoginPassword').click();
  await expect(page.locator('#navUserName')).toHaveText('Beta Farmer');

  // A 30-minute token is refreshed one minute before it expires, not at once.
  await page.clock.runFor(28 * 60 * 1000);
  expect(refreshBodies).toHaveLength(0);
  // Stop just after the refresh fires: jumping further while the request is
  // in flight would trip the client's own request timeout.
  await page.clock.runFor(61 * 1000);
  await expect.poll(() => refreshBodies.length).toBe(1);
  expect(refreshBodies[0]).toEqual({ refresh: 'refresh-0' });
  await expect.poll(() => page.evaluate(() => sessionStorage.getItem('km_refresh_token')))
    .toBe('refresh-1');

  // No refresh loop, and the next refresh sends the rotated token.
  await page.clock.runFor(10 * 60 * 1000);
  expect(refreshBodies).toHaveLength(1);
  await page.clock.runFor(20 * 60 * 1000);
  await expect.poll(() => refreshBodies.length).toBe(2);
  expect(refreshBodies[1]).toEqual({ refresh: 'refresh-1' });
});

test('an expired stored session without a refresh token loads logged out', async ({ page }) => {
  await page.clock.install({ time: DEVICE_NOW });
  await page.addInitScript(([token, receivedAt, storedUser]) => {
    if (sessionStorage.getItem('__seeded')) return;
    sessionStorage.setItem('__seeded', '1');
    localStorage.setItem('km_access_token', token);
    localStorage.setItem('km_access_received_at', String(receivedAt));
    localStorage.setItem('km_user', JSON.stringify(storedUser));
  }, [serverToken(0), DEVICE_NOW - 31 * 60 * 1000, user]);
  await page.route('**/api/**', route => route.fulfill({ contentType: 'application/json', body: '{}' }));

  await page.goto('/');
  await page.waitForFunction(() => Boolean(window.KM_Auth));

  await expect(page.locator('#navLoginBtn')).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem('km_access_token'))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('km_user'))).toBeNull();
});

test('a refresh answered after logout does not bring the session back', async ({ page }) => {
  await page.clock.install({ time: DEVICE_NOW });
  await preparePage(page);
  await page.route('**/api/token/', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ access: serverToken(0), refresh: 'refresh-0' }),
  }));
  await page.route('**/api/users/me/', route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(user),
  }));
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/api/token/refresh/', async route => {
    await gate;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access: serverToken(1), refresh: 'refresh-late' }),
    });
  });
  await page.route('**/api/users/logout/', route => route.fulfill({ contentType: 'application/json', body: '{}' }));

  await openAuth(page, 'password');
  await page.locator('#authUsernameInput').fill('farmer@example.com');
  await page.locator('#authPasswordInput').fill('strong-pass-123');
  await page.locator('#btnLoginPassword').click();
  await expect(page.locator('#navUserName')).toHaveText('Beta Farmer');

  await page.evaluate(() => window.KM_Auth.refreshToken());
  await page.evaluate(() => window.KM_Auth.logout());
  release();
  await page.waitForTimeout(200);

  expect(await page.evaluate(() => sessionStorage.getItem('km_refresh_token'))).toBeNull();
  expect(await page.evaluate(() => localStorage.getItem('km_access_token'))).toBeNull();
  await expect(page.locator('#navLoginBtn')).toBeVisible();
});
