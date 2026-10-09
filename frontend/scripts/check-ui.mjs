// Small responsive smoke check with synthetic data; never contacts Gmail or /ask.
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import assert from "node:assert/strict";
import {
  email,
  inbox,
  accountData,
  generated,
  supported,
  clarification,
} from "../src/test/fixtures.ts";
const longEmail = {
  ...email,
  subject:
    email.subject + " — " + "تفاصيل التسجيل Important information ".repeat(6),
  from: "فريق التواصل " + "long-sender-".repeat(12) + "@example.invalid",
  summary: "ملخص عربي مع English context. ".repeat(22),
  body: "نص أصلي English reference ABC123 <script>not executed</script>\n".repeat(
    25,
  ),
  predictions: ["Events", "Registration", "Updates", "Other"].map(
    (category) => ({ category }),
  ),
};
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
        const requestBody =
          path === "/api/ask" ? route.request().postDataJSON() : null;
        const askResponse =
          requestBody?.email_id || requestBody?.question === "supported"
            ? {
                ...supported,
                answer:
                  "يبدأ الموعد يوم الاثنين 12 October. راجع الشروط في المصدر. [email_id=11]\n".repeat(
                    8,
                  ),
                sources: [
                  {
                    ...supported.sources[0],
                    subject: longEmail.subject,
                    from: longEmail.from,
                  },
                ],
              }
            : requestBody?.question === "clarify"
              ? clarification
              : requestBody?.question === "none"
                ? {
                    status: "insufficient_evidence",
                    answer: "لا توجد معلومات كافية في البريد للإجابة.",
                    sources: [],
                    citations: [],
                  }
                : generated;
        const searchResponse = {
          query: "synthetic",
          count:
            new URL(route.request().url()).searchParams.get("q") === "empty"
              ? 0
              : 1,
          results:
            new URL(route.request().url()).searchParams.get("q") === "empty"
              ? []
              : [
                  {
                    email: longEmail,
                    matched_text:
                      "مقطع مطابق من المصدر Mixed English reference ABC123 <img src=x> ".repeat(
                        12,
                      ),
                    score: 0.82,
                  },
                ],
        };
        const data =
          path === "/api/gmail/accounts"
            ? accountData
            : path === "/api/emails"
              ? {
                  ...inbox,
                  total: 3,
                  count: 3,
                  emails: [
                    longEmail,
                    {
                      ...email,
                      id: 12,
                      subject: "Your registration is confirmed",
                      from: "events@example.invalid",
                      priority_level: "low",
                      tasks: [],
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
                ? longEmail
                : path === "/api/ask"
                  ? askResponse
                  : path === "/api/search/semantic"
                    ? searchResponse
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
    await page.getByRole("heading", { name: longEmail.subject }).waitFor();
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
    await page.getByRole("heading", { name: longEmail.subject }).click();
    await page.getByText("نص البريد الأصلي المخزن").waitFor();
    await capture("detail");
    await page.goBack();
    await page.getByRole("heading", { name: longEmail.subject }).waitFor();
    await page.goForward();
    await page.getByText("نص البريد الأصلي المخزن").waitFor();
    await page.getByRole("link", { name: "العودة إلى البريد الوارد" }).click();
    await page.getByRole("heading", { name: longEmail.subject }).waitFor();
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
    async function askCase(question) {
      await page.getByLabel("سؤالك").fill(question);
      await page
        .getByRole("button", { name: "اسأل البريد", exact: true })
        .click();
    }
    await askCase("supported");
    await page.getByText("مدعوم من البريد", { exact: true }).waitFor();
    await capture("ask-supported");
    await askCase("clarify");
    await page.getByText("لنحدد البريد المقصود").waitFor();
    await capture("ask-clarification");
    const option = page.getByRole("button", { name: /طلب الجهة الأولى/ });
    await option.focus();
    await page.keyboard.press("Enter");
    await page.getByText("مدعوم من البريد", { exact: true }).waitFor();
    await askCase("none");
    await page.getByText("لا توجد أدلة كافية").waitFor();
    await capture("ask-insufficient");
    if (width < 760)
      await page.getByRole("button", { name: "فتح القائمة" }).click();
    await page.getByRole("link", { name: "البحث", exact: true }).click();
    await page.getByLabel("ما الذي تبحث عنه؟").fill("synthetic travel");
    await page.getByRole("button", { name: "بحث", exact: true }).click();
    await page.getByRole("heading", { name: longEmail.subject }).waitFor();
    await capture("search-results");
    await page.getByRole("heading", { name: longEmail.subject }).click();
    await page.getByText("نص البريد الأصلي المخزن").waitFor();
    await page.goBack();
    await page.getByRole("heading", { name: longEmail.subject }).waitFor();
    assert.equal(
      await page.getByLabel("ما الذي تبحث عنه؟").inputValue(),
      "synthetic travel",
    );
    assert.equal(new URL(page.url()).search, "");
    await page.getByLabel("ما الذي تبحث عنه؟").fill("empty");
    await page.getByRole("button", { name: "بحث", exact: true }).click();
    await page.getByText("لا توجد نتائج", { exact: true }).waitFor();
    await capture("search-empty");
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
