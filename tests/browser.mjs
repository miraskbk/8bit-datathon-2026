/** Browser contract tests. All analysis responses are synthetic fixtures. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium } from 'playwright';
const base = process.env.UI_TEST_BASE || 'http://127.0.0.1:8004';
const browser = await chromium.launch({ headless: true, channel: process.env.UI_TEST_CHANNEL || undefined });
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
await page.route('**/ready', route => route.fulfill({ json: { status: 'ready' } }));
const jobId = 'b'.repeat(32);
let polls = 0;
const evidence = '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAgAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA//9k=';
await page.route('**/api/v1/analyze', async route => {
  assert.equal(route.request().headers()['x-api-key'], 'browser-contract-test-key-32-characters');
  await route.fulfill({ status: 202, json: { job_id: jobId, status: 'processing' } });
});
await page.route(`**/api/v1/jobs/${jobId}`, async route => {
  polls++;
  await route.fulfill({ json: polls === 1 ? { job_id: jobId, status: 'processing' } : {
    job_id: jobId, status: 'done', verdict: 'violation', metadata: { warnings: ['Synthetic browser contract fixture'] },
    violations: [{ type: 'Synthetic event', timecode_sec: 4.2, description: 'Fixture observation for UI testing only',
      evidence_frames: [{ timestamp_sec: 4.2, image_base64: evidence }], rule: { document: 'Правила № 231', section: 'п. 20', url: 'https://adilet.zan.kz/rus/docs/V1900019680' } }]
  } });
});
try {
  await page.goto(base);
  await page.waitForFunction(() => document.querySelector('#service-status')?.dataset.ready === 'true');
  assert(await page.locator('#analyze-button').isDisabled());
  await fs.mkdir('local-evaluation/ui', { recursive: true });
  await page.screenshot({ path: 'local-evaluation/ui/desktop-empty.png', fullPage: true });
  await page.locator('#api-key').fill('browser-contract-test-key-32-characters');
  await page.locator('#video-input').setInputFiles({ name: 'wrong.mp4', mimeType: 'video/mp4', buffer: Buffer.from('test') });
  assert.match(await page.locator('#error').innerText(), /\.mov/);
  await page.locator('#video-input').setInputFiles({ name: 'empty.mov', mimeType: 'video/quicktime', buffer: Buffer.alloc(0) });
  assert.match(await page.locator('#error').innerText(), /пустой/);
  await page.locator('#video-input').setInputFiles({ name: 'fixture.mov', mimeType: 'video/quicktime', buffer: Buffer.from('synthetic, server response intercepted') });
  assert(await page.locator('#analyze-button').isEnabled());
  await page.locator('#analyze-button').click();
  await page.locator('#results').waitFor({ state: 'visible' });
  assert.match(await page.locator('#verdict-title').innerText(), /Обнаружены признаки возможных нарушений/);
  assert.equal(await page.locator('.timecode').innerText(), '00:04.2');
  await page.waitForFunction(() => document.querySelector('.frames img').naturalWidth === 64);
  assert.equal(await page.locator('.frames img').evaluate(image => getComputedStyle(image).objectFit), 'contain');
  assert.equal(await page.locator('.rule-link').getAttribute('href'), 'https://adilet.zan.kz/rus/docs/V1900019680');
  assert.equal(await page.evaluate(() => sessionStorage.getItem('forte_api_key')), null);
  await page.route(`**/api/v1/jobs/${jobId}`, route => route.fulfill({ json: { job_id: jobId, status: 'done', verdict: 'no_violation', violations: [], metadata: {} } }));
  await page.locator('#analyze-button').click();
  await page.waitForFunction(() => document.querySelector('#verdict-title').textContent === 'Нарушение не обнаружено');
  assert.equal(await page.locator('.event').count(), 0);
  await page.route('**/api/v1/analyze', route => route.fulfill({ status: 401, json: { detail: 'Unauthorized fixture' } }));
  await page.locator('#analyze-button').click();
  await page.waitForFunction(() => document.querySelector('#error').textContent.includes('Неверный'));
  assert(await page.locator('#results').isHidden());
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'local-evaluation/ui/mobile.png', fullPage: true });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile overflow');
  await page.goto(base + '/docs');
  assert.match(await page.locator('h1').innerText(), /API проверки видео/);
  assert.equal(errors.length, 0, errors.join('\n'));
  console.log('UI_OK: desktop/mobile, file errors, positive/negative results, timestamps, source links, auth error, key storage, offline API guide');
} finally {
  await browser.close();
}
