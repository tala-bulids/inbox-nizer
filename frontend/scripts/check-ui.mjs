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
  taskPage,
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
  predictions: [
    "Events & Invitations",
    "Reminders",
    "Personal",
    "Business",
  ].map((category) => ({ category })),
};
const output = resolve(process.env.UI_ARTIFACT_DIR || "test-results");
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  channel: process.env.UI_BROWSER || "msedge",
  headless: true,
});
const results = [];
const browserAuth = process.env.UI_BROWSER_AUTH === "1";
const csrf = "a".repeat(64);
try {
  for (const width of [1440, 820, 390]) {
    const context = await browser.newContext({
      viewport: { width, height: 900 },
    });
    const page = await context.newPage();
    const errors = [];
    const askRequests = [];
    let signedIn = false;
    page.on("pageerror", (e) => errors.push(e.name));
    await page.route(
      new URL(process.env.UI_URL || "http://localhost:5173").origin + "/api/**",
      async (route) => {
        const path = new URL(route.request().url()).pathname;
        if (path === "/api/email-categories") {
          await route.fulfill({
            json: [
              "Business",
              "Customer Support",
              "Events & Invitations",
              "Finance & Bills",
              "Job Application",
              "Newsletters",
              "Personal",
              "Promotions",
              "Reminders",
              "Travel & Bookings",
            ],
          });
          return;
        }
        if (!browserAuth && path === "/api/auth/session") {
          await route.fulfill({ status: 401, json: {} });
          return;
        }
        if (path === "/api/auth/google/login/start") {
          signedIn = true;
          await route.fulfill({
            json: {
              authorization_url:
                "https://accounts.google.com/o/oauth2/auth?state=synthetic",
            },
          });
          return;
        }
        if (browserAuth) {
          const request = route.request();
          if (path === "/api/auth/session") {
            if (request.method() === "POST") {
              assert.equal(
                request.headers().authorization,
                "Bearer synthetic-ui-token",
              );
              signedIn = true;
            }
            if (request.method() === "DELETE") {
              assert.equal(request.headers()["x-csrf-token"], csrf);
              signedIn = false;
              await route.fulfill({ status: 204 });
            } else {
              await route.fulfill({
                status: signedIn ? 200 : 401,
                contentType: "application/json",
                body: JSON.stringify(signedIn ? { csrf_token: csrf } : {}),
              });
            }
            return;
          }
          assert.equal(request.headers().authorization, undefined);
          if (request.method() !== "GET")
            assert.equal(request.headers()["x-csrf-token"], csrf);
        }
        const requestBody =
          path === "/api/ask" ? route.request().postDataJSON() : null;
        if (requestBody) askRequests.push(requestBody);
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
        if (path === "/api/gmail/accounts/2/sync") {
          await new Promise((resolve) => setTimeout(resolve, 900));
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
              count: 2,
              success_count: 2,
              failed_count: 0,
              enrichment_failed: 0,
            }),
          });
          return;
        }
        const data =
          path === "/api/gmail/accounts"
            ? {
                accounts: [
                  {
                    ...accountData.accounts[0],
                    last_synced_at: "2026-10-08T12:00:00Z",
                  },
                ],
              }
            : path === "/api/tasks"
              ? {
                  ...taskPage,
                  tasks: taskPage.tasks.map((task, index) =>
                    index === 0
                      ? {
                          ...task,
                          task:
                            task.task +
                            " — " +
                            "إكمال المستندات المطلوبة Important action ".repeat(
                              12,
                            ),
                        }
                      : task,
                  ),
                }
              : path === "/api/auth/google/start"
                ? {
                    authorization_url:
                      "https://accounts.google.com/o/oauth2/auth?state=synthetic",
                  }
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
    await page
      .getByRole("heading", { name: "أهلاً بك في صندوقك الوارد المرتب" })
      .waitFor();
    await capture("login-ar");
    await page.getByRole("button", { name: "Switch to English" }).click();
    await page
      .getByRole("heading", { name: "Welcome to your organized inbox" })
      .waitFor();
    await capture("login-en");
    await page.getByRole("button", { name: "التبديل للعربية" }).click();
    if (browserAuth) {
      assert.equal(await page.locator('input[type="password"]').count(), 0);
      assert.equal(
        await page.getByText("دخول تطويري", { exact: true }).count(),
        0,
      );
      await page.route("https://accounts.google.com/**", (route) =>
        route.fulfill({
          status: 302,
          headers: { location: process.env.UI_URL || "http://localhost:5173" },
        }),
      );
      await page
        .getByRole("button", { name: "المتابعة باستخدام Google" })
        .click();
    } else {
      await page.getByLabel("رمز الوصول التطويري").fill("synthetic-ui-token");
      await page.getByRole("button", { name: "فتح مساحة العمل" }).click();
    }
    await page.getByRole("heading", { name: longEmail.subject }).waitFor();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
    async function capture(name) {
      await page.evaluate(() => window.scrollTo(0, 0));
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
    const categories = page.getByRole("button", { name: /التصنيف/ });
    await categories.click();
    assert.equal(await page.getByRole("checkbox").count(), 10);
    async function toggleCategory(name, count) {
      await page.getByRole("checkbox", { name, exact: true }).click();
      await page.waitForFunction(
        (expected) =>
          document.querySelectorAll(".category-option input:checked").length ===
          expected,
        count,
      );
    }
    await toggleCategory("شخصي", 1);
    await toggleCategory("سفر وحجوزات", 2);
    assert.deepEqual(new URL(page.url()).searchParams.getAll("category"), [
      "Personal",
      "Travel & Bookings",
    ]);
    await capture("inbox-categories");
    await toggleCategory("شخصي", 1);
    await toggleCategory("سفر وحجوزات", 0);
    await page.keyboard.press("Escape");
    assert.equal(await categories.getAttribute("aria-expanded"), "false");
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
    const completedAnswer = await page
      .getByTestId("conversational-answer")
      .innerText();
    assert.doesNotMatch(completedAnswer, /email_id|chunk_id/);
    await page.getByText("المصادر (1)", { exact: true }).click();
    await page.locator(".source-cards a").first().click();
    await page.getByText("نص البريد الأصلي المخزن").waitFor();
    await page.getByRole("link", { name: "العودة إلى الإجابة" }).click();
    assert.equal(
      await page.getByTestId("conversational-answer").innerText(),
      completedAnswer,
    );
    assert.equal(askRequests.length, 2);
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
    if (width < 760)
      await page.getByRole("button", { name: "فتح القائمة" }).click();
    await page.getByRole("link", { name: "المهام", exact: true }).click();
    await page.getByText("لا يوجد موعد مستخرج", { exact: true }).waitFor();
    await capture("tasks");
    assert.equal(
      await page
        .getByRole("button", { name: "الأحدث", exact: true })
        .getAttribute("aria-pressed"),
      "true",
    );
    await page.getByRole("button", { name: "الأقدم", exact: true }).click();
    await page
      .getByRole("button", { name: "الأقدم", exact: true })
      .and(page.locator('[aria-pressed="true"]'))
      .waitFor();
    await page
      .getByLabel("الموعد النهائي", { exact: true })
      .selectOption("true");
    await page.waitForURL((url) => url.searchParams.get("deadline") === "true");
    const tasksPath = new URL(page.url()).pathname + new URL(page.url()).search;
    await page.locator(".task-source").first().click();
    await page.getByText("نص البريد الأصلي المخزن").waitFor();
    await page.getByRole("link", { name: "العودة إلى المهام" }).click();
    await page
      .getByRole("button", { name: "الأقدم", exact: true })
      .and(page.locator('[aria-pressed="true"]'))
      .waitFor();
    assert.equal(
      new URL(page.url()).pathname + new URL(page.url()).search,
      tasksPath,
    );
    assert.equal(
      await page
        .getByRole("button", { name: "الأقدم", exact: true })
        .getAttribute("aria-pressed"),
      "true",
    );
    assert.equal(
      await page.getByLabel("الموعد النهائي", { exact: true }).inputValue(),
      "true",
    );
    if (width < 760)
      await page.getByRole("button", { name: "فتح القائمة" }).click();
    await page.getByRole("link", { name: "الإعدادات", exact: true }).click();
    await page.getByText("متصل", { exact: true }).waitFor();
    await capture("settings-connected");
    await page
      .getByRole("button", { name: "مزامنة الآن", exact: true })
      .click();
    await page.getByText(/جارٍ مزامنة البريد/).waitFor();
    await capture("settings-sync-pending");
    await page.getByText(/تمت معالجة/).waitFor();
    await capture("settings-sync-success");
    const reconnect = page.getByRole("button", {
      name: "إعادة الاتصال",
      exact: true,
    });
    await reconnect.focus();
    await page.keyboard.press("Enter");
    await page.getByRole("link", { name: "متابعة إلى Google" }).waitFor();
    await capture("settings-oauth");
    assert.equal(
      await page.evaluate(() => localStorage.length + sessionStorage.length),
      0,
    );
    await page.getByRole("button", { name: "Switch to English" }).click();
    for (const [label, heading, shot] of [
      ["Inbox", "Inbox", "inbox"],
      ["Ask Mail", "Ask Mail", "ask"],
      ["Search", "Find your email", "search"],
      ["Tasks", "Tasks", "tasks"],
      ["Settings", "Account & connection", "settings"],
    ]) {
      if (width < 760)
        await page.getByRole("button", { name: "Open menu" }).click();
      await page.getByRole("link", { name: label, exact: true }).click();
      await page.getByRole("heading", { name: heading, exact: true }).waitFor();
      assert.equal(await page.locator("html").getAttribute("dir"), "ltr");
      await capture("english-" + shot);
    }
    await page.getByRole("button", { name: "التبديل للعربية" }).click();
    if (browserAuth) {
      await page.reload();
      await page.getByText("متصل", { exact: true }).waitFor();
      await page.goto(
        new URL("/unknown-page", process.env.UI_URL || "http://localhost:5173")
          .href,
      );
      await page.getByRole("heading", { name: "الصفحة غير موجودة" }).waitFor();
      await capture("not-found");
      await page.getByRole("button", { name: "خروج", exact: true }).click();
      await page
        .getByRole("button", { name: "المتابعة باستخدام Google" })
        .waitFor();
      await capture("browser-login");
      assert.equal(signedIn, false);
      for (const result of ["success", "denied", "expired", "provider_error"]) {
        await page.goto(
          new URL(
            "/oauth/complete?result=" + result,
            process.env.UI_URL || "http://localhost:5173",
          ).href,
        );
        await page
          .getByRole("link", { name: "الانتقال إلى الإعدادات" })
          .waitFor();
        await capture("oauth-" + result);
      }
    }
    assert.deepEqual(errors, []);
    results.push({
      width,
      rtl: true,
      noOverflow: true,
      mobileFocusRestored: width < 760 ? true : null,
      generatedWarning: true,
      googleOnlyProductionLogin: browserAuth,
      askSourceBackRestored: true,
      tasksFilterBackRestored: true,
      languages: ["ar", "en"],
      apiTransport:
        "synthetic mocks; no live Google consent, Gmail sync, or mailbox reads",
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
