import { chromium } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
const base = process.env.UI_BASE_URL || 'http://127.0.0.1:4193';
const out = process.env.UI_EVIDENCE_DIR || '../audit/remediation/baseline';
await mkdir(out, { recursive: true });
const browser = await chromium.launch();
const results = [];
try {
  for (const width of [320, 360, 768, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, reducedMotion: 'reduce' });
    await page.addInitScript(() => { localStorage.setItem('km_lang', 'en'); localStorage.setItem('km_theme', 'light'); });
    await page.goto(base);
    await page.waitForFunction(() => typeof window.showService === 'function');
    for (const service of ['home', 'weather', 'market-prices', 'crop-recommendations', 'pest-control', 'government-schemes', 'ai-assistant', 'field-advisory']) {
      await page.evaluate(s => window.showService(s), service);
      await page.screenshot({ path: `${out}/${width}-${service}.png`, fullPage: true, animations: 'disabled' });
      results.push({ width, service, ...await page.evaluate(() => ({
        overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        main: document.querySelectorAll('main').length,
        overflowElements: [...document.querySelectorAll('main *')].filter(el => {
          const r = el.getBoundingClientRect();
          return r.width && (r.right > innerWidth + 1 || r.left < -1);
        }).slice(0, 12).map(el => ({ tag: el.tagName, id: el.id, class: el.className, width: el.getBoundingClientRect().width })),
        title: document.title,
      })) });
    }
    await page.close();
  }
  await writeFile(`${out}/screens.json`, JSON.stringify(results, null, 2));
} finally { await browser.close(); }
console.log(JSON.stringify(results));
