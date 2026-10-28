// Real local backend/model integration. No fetch interception or canned answers.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
const base = process.env.SHOWCASE_URL || 'http://127.0.0.1:4181';
const output = '../results/phase3-browser';
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const results = [];
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 900 }, serviceWorkers: 'block' });
    const page = await context.newPage();
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push(new URL(request.url()).pathname));
    await page.goto(base);
    await page.getByRole('button', { name: 'Switch to English' }).click();
    await page.getByText(/Collection reference date/).waitFor();
    assert.equal(await page.getByRole('checkbox').count(), 0);
    await page.getByRole('button', { name: 'What meetings do I have this week?', exact: true }).click();
    await page.getByRole('button', { name: 'Ask AI', exact: true }).click();
    const answer = page.getByRole('region', { name: 'Answer', exact: true });
    await answer.getByText(/Conflicting evidence; no single date selected/).waitFor({ timeout: 120000 });
    await page.screenshot({ path: `${output}/${width}-meetings.png`, fullPage: true });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.getByRole('link', { name: 'Smart Tasks', exact: true }).click();
    await page.getByLabel('Choose a source').selectOption('7');
    await page.getByRole('button', { name: 'Extract tasks', exact: true }).click();
    await page.getByText('Responsible: Maya', { exact: true }).waitFor();
    await page.getByText('Deadline state: Explicit', { exact: true }).waitFor();
    await page.getByRole('link', { name: 'Open supporting email' }).click();
    assert.equal(await page.getByLabel('Choose a source').inputValue(), '7');
    await page.getByRole('button', { name: 'التبديل للعربية' }).click();
    await page.getByRole('link', { name: 'المهام الذكية', exact: true }).click();
    await page.getByLabel('اختر مصدراً').selectOption('14');
    await page.getByRole('button', { name: 'استخرج المهام', exact: true }).click();
    await page.getByText('المسؤول: ليلى', { exact: true }).waitFor();
    await page.getByText('حالة الموعد: غير مذكور', { exact: true }).waitFor();
    await page.getByText('المصدر الأصلي', { exact: true }).click();
    await page.screenshot({ path: `${output}/${width}-tasks-ar.png`, fullPage: true });
    assert.equal(await page.locator('html').getAttribute('dir'), 'rtl');
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.equal((await page.reload()).status(), 200);
    await page.getByLabel('اختر مصدراً').waitFor();
    assert.equal(await page.getByLabel('اختر مصدراً').inputValue(), '14');
    assert.deepEqual(errors, []);
    assert.equal((await context.cookies()).length, 0);
    assert(!requests.some(path => path.startsWith('/api/') && !path.startsWith('/api/showcase/')));
    results.push({ width, realE5: true, conflictShown: true, ownerShown: true, missingDeadlineShown: true,
      sourceNavigation: true, rtl: true, noOverflow: true, refresh: true, pageErrors: 0, privateApiRequests: 0, cookies: 0 });
    await context.close();
  }
} finally { await browser.close(); }
await writeFile(`${output}/report.json`, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results));
