// Synthetic fixture only: invoked by the opt-in unittest, never real review data.
import { chromium } from '../frontend/node_modules/playwright/index.mjs';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
const url = process.argv[2];
const origin = new URL(url).origin;
const browser = await chromium.launch({channel: 'msedge', headless: true});
try {
  const page = await browser.newPage({viewport: {width: 1100, height: 1000}});
  const errors = [];
  const external = [];
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('request', (request) => {if (!request.url().startsWith(origin + '/')) external.push(request.url());});
  await page.goto(url);
  await page.getByText('0 / 50 reviewed', {exact: false}).waitFor();
  assert.equal(await page.locator('#labels button').count(), 10);
  assert.equal(await page.getByRole('button', {name: 'Business', exact: true}).isDisabled(), false);
  for (const name of ['Business', 'Ambiguous']) {
    await page.getByRole('button', {name, exact: true}).click();
    assert.equal(await page.getByRole('textbox', {name: 'Your reviewer name'}).evaluate((input) => document.activeElement === input), true);
    assert.equal(await page.locator('#progress').textContent(), '0 / 50 reviewed · 0 skipped · Email 1 of 50');
  }
  await page.getByRole('textbox', {name: 'Your reviewer name'}).fill('Synthetic reviewer');
  await page.getByRole('button', {name: 'Business', exact: true}).click();
  await page.getByText('1 / 50 reviewed', {exact: false}).waitFor();
  await page.getByRole('button', {name: '← Previous', exact: true}).click();
  await page.getByText('Saved: Business · Synthetic reviewer', {exact: true}).waitFor();
  await page.getByRole('button', {name: 'Ambiguous', exact: true}).click();
  await page.getByText('Email 2 of 50', {exact: false}).waitFor();
  await page.getByRole('button', {name: 'Skip →', exact: true}).click();
  await page.getByText('Email 3 of 50', {exact: false}).waitFor();
  await page.reload();
  await page.getByText('1 / 50 reviewed · 1 skipped · Email 3 of 50', {exact: true}).waitFor();
  assert.equal(await page.getByRole('textbox', {name: 'Your reviewer name'}).inputValue(), 'Synthetic reviewer');
  const storage = await page.evaluate(() => Object.keys(localStorage));
  assert.deepEqual(storage, ['local-reviewer-name']);
  await mkdir('results/local-classifier-review', {recursive: true});
  for (const width of [1100, 390]) {
    await page.setViewportSize({width, height: 1000});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({path: `results/local-classifier-review/synthetic-${width}.png`, fullPage: true});
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  // Embedded browser storage may be unavailable entirely, or writes may fail
  // after successful reads. Both must leave labeling usable.
  for (const mode of ['blocked', 'write-fails']) {
    const context = await browser.newContext();
    const storagePage = await context.newPage();
    const storageErrors = [];
    storagePage.on('pageerror', (error) => storageErrors.push(error.name));
    await storagePage.addInitScript((mode) => {
      if (mode === 'blocked') {
        Object.defineProperty(window, 'localStorage', {get() {throw new DOMException('Storage blocked', 'SecurityError');}});
      } else {
        Storage.prototype.setItem = () => {throw new DOMException('Storage unavailable', 'QuotaExceededError');};
      }
    }, mode);
    await storagePage.goto(url);
    await storagePage.locator('#labels button').first().waitFor();
    assert.equal(await storagePage.locator('#labels button').count(), 10);
    const oldProgress = await storagePage.locator('#progress').textContent();
    const completed = Number(oldProgress.split(' / ')[0]);
    await storagePage.getByRole('textbox', {name: 'Your reviewer name'}).fill('Synthetic storage test');
    await storagePage.getByRole('button', {name: 'Business', exact: true}).click();
    await storagePage.getByText(`${completed + 1} / 50 reviewed`, {exact: false}).waitFor();
    await storagePage.getByText('Saved to development.csv ✓', {exact: true}).waitFor();
    assert.deepEqual(storageErrors, []);
    await context.close();
  }
  console.log('PASS: ten labels, autosave, correction, ambiguity, skip/reload, desktop/mobile, no external requests, blocked storage and failed storage writes.');
} finally {await browser.close();}
