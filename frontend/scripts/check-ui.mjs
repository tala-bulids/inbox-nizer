// Small responsive smoke check with synthetic data; never contacts Gmail or /ask.
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import assert from "node:assert/strict";
import { email, inbox, accountData, generated } from "../src/test/fixtures.ts";
const output = resolve(process.env.UI_ARTIFACT_DIR || "test-results");
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  channel: process.env.UI_BROWSER || "msedge",
  headless: true,
});
const results = [];
try {
  for (const width of [1440, 820, 390]) {
    const context = await browser.newContext({
      viewport: { width, height: 900 },
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.name));
    await page.route(
      new URL(process.env.UI_URL || "http://localhost:5173").origin + "/api/**",
      async (route) => {
        const path = new URL(route.request().url()).pathname;
        const data =
          path === "/api/gmail/accounts"
            ? accountData
            : path === "/api/emails"
              ? {
                  ...inbox,
                  total: 3,
                  count: 3,
                  emails: [
                    email,
                    {
                      ...email,
                      id: 12,
                      subject: "Your registration is confirmed",
                      from: "events@example.invalid",
                      priority_level: "low",
                    },
                    {
                      ...email,
                      id: 13,
                      subject: "مستندات مطلوبة لاستكمال الطلب",
                      priority_level: "medium",
                    },
                  ],
                }
              : path.startsWith("/api/emails/")
                ? email
                : path === "/api/ask"
                  ? generated
                  : null;
        await route.fulfill({
          status: data ? 200 : 404,
          contentType: "application/json",
          body: JSON.stringify(data || {}),
        });
      },
    );
    await page.goto(process.env.UI_URL || "http://localhost:5173");
    await page.getByLabel("رمز الوصول التطويري").fill("synthetic-ui-token");
    await page.getByRole("button", { name: "فتح مساحة العمل" }).click();
    await page.getByRole("heading", { name: email.subject }).waitFor();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
    async function capture(name) {
      assert.equal(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
        true,
        `${width}: ${name} overflow`,
      );
      await page.screenshot({
        path: resolve(output, `${name}-${width}.png`),
        fullPage: true,
      });
    }
    await capture("inbox");
    await page.getByRole("heading", { name: email.subject }).click();
    await page.getByText("نص البريد الأصلي المخزن").waitFor();
    await capture("detail");
    await page.goBack();
    await page.getByRole("heading", { name: email.subject }).waitFor();
    if (width < 760) {
      const trigger = page.getByRole("button", { name: "فتح القائمة" });
      await trigger.click();
      await page.getByRole("dialog").waitFor();
      await page.keyboard.press("Escape");
      assert.equal(
        await trigger.evaluate((el) => el === document.activeElement),
        true,
      );
      await trigger.click();
    }
    await page.getByRole("link", { name: "اسأل البريد", exact: true }).click();
    await page.getByLabel("سؤالك").fill("Summarize the next steps");
    await page
      .getByRole("button", { name: "اسأل البريد", exact: true })
      .click();
    await page.getByRole("note").waitFor();
    await capture("ask-generated");
    assert.equal(
      await page.getByText("مدعوم من البريد", { exact: true }).count(),
      0,
    );
    assert.equal(
      await page.evaluate(() => localStorage.length + sessionStorage.length),
      0,
    );
    assert.deepEqual(errors, []);
    results.push({
      width,
      rtl: true,
      noOverflow: true,
      mobileFocusRestored: width < 760 ? true : null,
      generatedWarning: true,
      privateStorageEmpty: true,
      pageErrors: errors,
    });
    await context.close();
  }
} finally {
  await browser.close();
}
await writeFile(
  resolve(output, "responsive-check.json"),
  JSON.stringify(results, null, 2) + "\n",
);
console.log(JSON.stringify(results));
