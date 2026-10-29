// Opt-in browser acceptance against the actual locally provisioned AI backend.
import { chromium } from "playwright";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const base = process.env.SHOWCASE_URL || "http://127.0.0.1:4181";
const output = "../results/showcase-browser";
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "msedge", headless: true });
const results = [];
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({
      viewport: { width, height: 900 },
      serviceWorkers: "block",
    });
    const page = await context.newPage();
    const errors = [],
      requests = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => requests.push(new URL(r.url()).pathname));
    await page.goto(base);
    await page.getByRole("button", { name: "Switch to English" }).click();
    await page.getByLabel("Choose a source").waitFor();
    await page
      .getByRole("button", { name: "What is the Atlas workshop date?" })
      .click();
    await page.getByRole("button", { name: "Ask AI", exact: true }).click();
    await page
      .getByRole("link", { name: "Source 1", exact: true })
      .first()
      .waitFor({ timeout: 120000 });
    await page.getByRole("link", { name: /Open source/ }).click();
    assert.equal(await page.getByLabel("Choose a source").inputValue(), "1");
    await page.getByRole("link", { name: "Smart Tasks", exact: true }).click();
    await page
      .getByRole("button", { name: "Extract tasks", exact: true })
      .click();
    await page.getByText("2026-11-02", { exact: true }).waitFor();
    await page.getByText("Original source", { exact: true }).click();
    await page.getByRole("link", { name: "Model Lab", exact: true }).click();
    await page.getByRole("button", { name: "Playground", exact: true }).click();
    await page
      .getByRole("button", { name: "Run prediction", exact: true })
      .click();
    await page.getByText(/Model score:/).waitFor({ timeout: 90000 });
    await page.getByRole("link", { name: "Model Lab", exact: true }).click();
    await page.getByRole("button", { name: "Evaluation", exact: true }).click();
    await page.getByText(/quality gate FAILED/).waitFor();
    await page.screenshot({
      path: `${output}/${width}-en.png`,
      fullPage: true,
    });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.getByRole("button", { name: "التبديل للعربية" }).click();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
    await page.getByRole("link", { name: "اسأل البريد", exact: true }).click();
    await page
      .getByRole("button", { name: "ما تاريخ الورشة؟", exact: true })
      .click();
    await page
      .getByRole("button", { name: "اسأل البريد", exact: true })
      .click();
    await page
      .getByRole("link", { name: "المصدر 2", exact: true })
      .first()
      .waitFor({ timeout: 120000 });
    await page.screenshot({
      path: `${output}/${width}-ar.png`,
      fullPage: true,
    });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    for (const route of ["/intelligence?email=2", "/tasks?email=2", "/lab"]) {
      assert.equal((await page.goto(base + route)).status(), 200);
      await page
        .getByRole("link", { name: "مجموعة البريد", exact: true })
        .waitFor();
      assert.equal((await page.reload()).status(), 200);
    }
    assert.equal((await context.cookies()).length, 0);
    assert.deepEqual(errors, []);
    assert(
      !requests.some(
        (p) => p.startsWith("/api/") && !p.startsWith("/api/showcase/"),
      ),
    );
    results.push({
      width,
      english: true,
      arabic: true,
      classification: true,
      groundedAnswers: true,
      tasks: true,
      lab: true,
      deepLinks: true,
      noOverflow: true,
      pageErrors: 0,
      privateApiRequests: 0,
      cookies: 0,
    });
    await context.close();
  }
} finally {
  await browser.close();
}
await writeFile(`${output}/report.json`, JSON.stringify(results, null, 2));
console.log(JSON.stringify(results));
