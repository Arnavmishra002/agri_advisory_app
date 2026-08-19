import { expect, test } from '@playwright/test';

test('second chat turn sends only backend-supported history fields', async ({ page }, testInfo) => {
  const chatRequests = [];
  let answerNumber = 0;

  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: '{}',
  }));
  await page.route('**/api/chatbot/stream/', async route => {
    chatRequests.push(route.request().postDataJSON());
    answerNumber += 1;
    const answer = `Grounded answer ${answerNumber}`;
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream; charset=utf-8',
      body: [
        `data: ${JSON.stringify({ token: answer, full_text: answer })}`,
        `data: ${JSON.stringify({
          done: true,
          response: answer,
          intent: 'general',
          language: 'en',
          data_source: 'KrishiMitra KB (instant)',
          sources: ['Verified test knowledge'],
        })}`,
        '',
      ].join('\n\n'),
    });
  });
  await page.goto('/');
  await page.waitForFunction(() => typeof window.showService === 'function');
  const aiButton = testInfo.project.name.includes('mobile') ? '#bnav-ai' : '#nav-ai';
  await page.locator(aiButton).click();

  await page.locator('#messageInput').fill('first farmer question');
  await page.locator('#chatSendBtn').click();
  await expect(page.getByText('Grounded answer 1', { exact: true })).toBeVisible();

  await page.locator('#messageInput').fill('second farmer question');
  await page.locator('#chatSendBtn').click();
  await expect(page.getByText('Grounded answer 2', { exact: true })).toBeVisible();

  expect(chatRequests).toHaveLength(2);
  expect(chatRequests[1].history).toEqual([
    { role: 'user', content: 'first farmer question' },
    { role: 'assistant', content: 'Grounded answer 1' },
  ]);
});
