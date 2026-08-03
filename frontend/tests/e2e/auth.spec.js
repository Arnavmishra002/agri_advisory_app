import { expect, test } from '@playwright/test';

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
  await page.locator('#regPhoneInput').fill('9876543210');
  await page.locator('#regStateInput').fill('Uttar Pradesh');
  await page.locator('#btnRegister').click();

  await expect(page.locator('#navUserName')).toHaveText('Beta Farmer');
  expect(registrationBody.guest_session_token).toBe('signed-guest-token');
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
    '#regPhoneInput', '#regStateInput',
  ]) {
    await expect(page.locator(selector)).toHaveValue('');
  }
});

test('password login accepts email and refresh rotates only the access token', async ({ page }) => {
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
    body: '{"access":"new-access"}',
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
    .toBe('session-refresh');
});

test('expired OTP stays logged out and shows a farmer-safe error', async ({ page }) => {
  await preparePage(page);
  await page.route('**/api/users/otp/request/', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '{"success":true}',
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
