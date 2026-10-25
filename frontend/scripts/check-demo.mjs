// Runs against a real static production build. No API mocking or Gmail access.
import { chromium } from "playwright";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const base = process.env.DEMO_URL || "http://127.0.0.1:4173";
const output = resolve(
  process.env.DEMO_CHECK_OUTPUT || "../results/public-demo/browser-local",
);
const browser = await chromium.launch({
  channel: process.env.UI_BROWSER || "msedge",
  headless: true,
});
const results = [];
await mkdir(output, { recursive: true });
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({
      viewport: { width, height: 900 },
      serviceWorkers: "block",
    });
    const page = await context.newPage();
    const errors = [],
      violations = [],
      requests = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(m.text());
    });
    page.on("request", (request) => {
      requests.push(request.url());
      if (
        new URL(request.url()).origin !== new URL(base).origin ||
        /\/(api|auth|gmail)\//.test(new URL(request.url()).pathname) ||
        ["xhr", "fetch"].includes(request.resourceType())
      )
        violations.push(request.url());
    });
    await page.addInitScript(() => {
      window.demoCredentialReads = 0;
      const descriptor = Object.getOwnPropertyDescriptor(
        Document.prototype,
        "cookie",
      );
      Object.defineProperty(Document.prototype, "cookie", {
        configurable: true,
        get() {
          window.demoCredentialReads++;
          return descriptor.get.call(this);
        },
        set(value) {
          window.demoCredentialReads++;
          descriptor.set.call(this, value);
        },
      });
    });
    const response = await page.goto(base, {
      waitUntil: "networkidle",
      timeout: 60000,
    });
    assert.equal(response.status(), 200);
    await page.locator(".skip-link").waitFor({ state: "attached" });
    const entryUrl = page.url();
    await page.locator(".skip-link").focus();
    await page.keyboard.press("Enter");
    assert.equal(
      page.url(),
      entryUrl,
      "skip link must not navigate a hash route",
    );
    assert.equal(await page.evaluate(() => document.activeElement.id), "main");

    await page
      .getByText("عرض تفاعلي — بيانات تجريبية", { exact: true })
      .waitFor();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
    await page.screenshot({
      path: resolve(output, `${width}-ar.png`),
      fullPage: true,
    });
    await page.getByRole("button", { name: "Switch to English" }).click();
    await page.getByText("24 messages", { exact: true }).waitFor();
    assert.equal(await page.locator("html").getAttribute("dir"), "ltr");
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await page
      .getByText("Next milestone — prototype review", { exact: true })
      .waitFor();
    await page.getByRole("button", { name: "Previous", exact: true }).click();
    await page.getByRole("combobox", { name: /Priority/ }).selectOption("high");
    await page.getByText("5 messages", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Category All categories" }).click();
    await page
      .getByRole("checkbox", { name: "Job Application", exact: true })
      .click();
    await page.getByText("2 messages", { exact: true }).waitFor();
    await page.keyboard.press("Escape");
    await page
      .getByRole("link", { name: /Interview invitation — Cedar Studio/ })
      .click();
    await page
      .getByRole("heading", { name: "Example summary", exact: true })
      .waitFor();
    await page
      .getByText("Confirm interview availability", { exact: true })
      .waitFor();
    await page.reload({ waitUntil: "networkidle" });
    await page
      .getByRole("heading", {
        name: "Interview invitation — Cedar Studio",
        exact: true,
      })
      .waitFor();
    // Reload resets ephemeral language preference to Arabic, preserving no session storage.
    await page.getByRole("button", { name: "Switch to English" }).click();
    const menu = page.getByRole("button", { name: "Open menu", exact: true });
    if (await menu.isVisible()) await menu.click();
    await page.getByRole("link", { name: "Tasks", exact: true }).click();
    await page
      .getByText("Confirm interview availability", { exact: true })
      .waitFor();
    await page
      .getByRole("link", { name: /Source: Interview invitation/ })
      .click();
    await page
      .getByRole("heading", { name: "Example summary", exact: true })
      .waitFor();
    await page
      .getByRole("link", { name: "Features & limitations", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Gmail is not connected", exact: true })
      .waitFor();
    assert.ok(
      await page
        .getByRole("button", { name: "Connect Gmail unavailable in demo" })
        .isDisabled(),
    );
    assert.equal(
      await page.getByRole("button", { name: "Sign out", exact: true }).count(),
      0,
    );
    await page.screenshot({
      path: resolve(output, `${width}-en-about.png`),
      fullPage: true,
    });
    for (const path of [
      "/#/email/2",
      "/#/tasks",
      "/#/settings",
      "/#/unknown",
    ]) {
      await page.goto("about:blank");
      const direct = await page.goto(base.replace(/\/$/, "") + path, {
        waitUntil: "networkidle",
      });
      assert.equal(direct.status(), 200);
      await page
        .getByText("عرض تفاعلي — بيانات تجريبية", { exact: true })
        .waitFor();
      await page.reload({ waitUntil: "networkidle" });
      await page
        .getByText("عرض تفاعلي — بيانات تجريبية", { exact: true })
        .waitFor();
      assert.ok(await page.locator("h1").count());
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth > innerWidth + 1,
        ),
        false,
        "horizontal overflow",
      );
      assert.equal(await page.evaluate(() => window.demoCredentialReads), 0);
    }
    assert.deepEqual(await context.cookies(), []);
    assert.deepEqual(violations, []);
    assert.deepEqual(errors, []);
    results.push({
      width,
      languages: ["ar", "en"],
      inbox: true,
      detail: true,
      filters: true,
      pagination: true,
      tasks: true,
      deep_link_refresh: true,
      no_credentials_or_api: true,
      requests: requests.length,
      errors,
    });
    await context.close();
  }
  const context = await browser.newContext();
  const info = await context.request.get(
    new URL("/demo-build.json", base).href,
  );
  assert.equal(info.status(), 200);
  const build = await info.json();
  assert.equal(build.mode, "synthetic-demo");
  if (process.env.DEMO_EXPECTED_SHA)
    assert.equal(build.commit, process.env.DEMO_EXPECTED_SHA);
  const report = { url: base, build, results, passed: true };
  await writeFile(
    resolve(output, "report.json"),
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report));
  await context.close();
} finally {
  await browser.close();
}
