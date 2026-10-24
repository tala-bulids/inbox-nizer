// Real browser, production SPA, synthetic API only. Never contact Gmail.
import assert from "node:assert/strict";
import { chromium } from "playwright";
import { email, accountData } from "../src/test/fixtures.ts";

const origin = process.env.UI_URL || "http://127.0.0.1:8766";
const browser = await chromium.launch({ channel: "msedge", headless: true });
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    let status = "connected", count = 0, calls = 0;
    const before = new Date(Date.now() - 1000).toISOString();
    let stamp = before;
    let manualStarted = false;
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.name));
    await page.route(new URL(origin).origin + "/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      if (path === "/api/auth/session") return route.fulfill({ json: { csrf_token: "a".repeat(64) } });
      if (path === "/api/email-categories") return route.fulfill({ json: [] });
      if (path === "/api/gmail/accounts") return route.fulfill({ json: {
        runtime_profile: "render-free", sync_interval_seconds: 86400 * 365,
        accounts: [{ ...accountData.accounts[0], status, last_synced_at: stamp,
          message_count: count, sync_pending: manualStarted && calls < 3,
          initial_sync_pending: false }],
      } });
      if (path.endsWith("/sync")) {
        assert.equal(status, "connected");
        assert.equal(route.request().headers()["x-csrf-token"], "a".repeat(64));
        calls++;
        assert.ok(calls <= 3, "continuation must terminate");
        await new Promise((resolve) => setTimeout(resolve, 700));
        count += 5;
        if (calls === 3) stamp = new Date().toISOString();
        return route.fulfill({ json: { count: 5, success_count: 5, failed_count: 0,
          enrichment_failed: 0, has_more: calls < 3, progress_token: `page-${calls}` } });
      }
      if (path.endsWith("/connection")) {
        assert.equal(route.request().method(), "DELETE");
        status = "disconnected";
        return route.fulfill({ status: 204 });
      }
      if (path === "/api/auth/google/start") return route.fulfill({ json: {
        authorization_url: "https://accounts.google.com/o/oauth2/auth?state=synthetic",
      } });
      if (path === "/api/emails") return route.fulfill({ json: {
        count, total: count, limit: 20, offset: 0,
        emails: Array.from({ length: count }, (_, i) => ({ ...email, id: i + 1,
          message_id: `synthetic-${i}`, subject: `Saved message ${i + 1}` })),
      } });
      return route.fulfill({ status: 404, json: {} });
    });
    await page.goto(origin + "/settings");
    const update = page.getByRole("button", { name: "تحديث الآن", exact: true });
    await update.waitFor();
    assert.equal(calls, 0);
    manualStarted = true;
    await update.click();
    const updating = page.getByRole("button", { name: "جاري التحديث...", exact: true });
    await updating.waitFor();
    assert.equal(await updating.isDisabled(), true);
    await page.getByText("تم تحديث البريد", { exact: true }).waitFor();
    assert.equal(calls, 3);
    assert.equal(count, 15);
    assert.notEqual(stamp, before);
    await page.reload();
    await update.waitFor();
    assert.equal(calls, 3);
    await page.getByRole("button", { name: "قطع اتصال Gmail", exact: true }).click();
    await page.getByText("غير متصل", { exact: true }).waitFor();
    assert.equal(await update.isDisabled(), true);
    await page.reload();
    await page.getByRole("button", { name: "إعادة الاتصال", exact: true }).click();
    await page.getByRole("link", { name: "متابعة إلى Google" }).waitFor();
    // Simulate successful same-account consent without a Google request.
    status = "connected";
    await page.reload();
    await update.waitFor();
    assert.equal(await update.isDisabled(), false);
    assert.equal(calls, 3);
    await page.goto(origin + "/");
    await page.getByRole("heading", { name: "Saved message 15", exact: true }).waitFor();
    for (const path of ["/search", "/ask"]) {
      await page.goto(origin + path);
      await page.getByRole("heading", { name: "الصفحة غير موجودة" }).waitFor();
    }
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ width, pages: calls, savedMessages: count,
      reload: true, disconnectReconnect: true, hostedRoutesBlocked: true,
      api: "synthetic; no live Google consent or mailbox access" }));
    await context.close();
  }
} finally {
  await browser.close();
}
