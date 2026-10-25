// Real /ask responses come from the isolated pytest database bridge.
import { chromium } from "playwright";
import assert from "node:assert/strict";
import { accountData } from "../src/test/fixtures.ts";
const browser = await chromium.launch({ channel: "msedge", headless: true });
try {
  const page = await browser.newPage();
  const requests = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") console.log(msg.text());
  });
  page.on("requestfailed", (req) => console.log(req.url(), req.failure()));
  page.on("pageerror", (error) => console.log(error.message));
  await page.route("http://localhost:5189/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/auth/session")
      return route.fulfill({
        status: 200,
        json: { csrf_token: "a".repeat(64) },
      });
    if (path === "/api/gmail/accounts")
      return route.fulfill({ json: accountData });
    if (path === "/api/ask") {
      const body = route.request().postDataJSON();
      requests.push(body);
      const response = await fetch(process.env.ASK_TEST_BRIDGE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return route.fulfill({
        status: response.status,
        json: await response.json(),
      });
    }
    return route.fulfill({ status: 404, json: {} });
  });
  await page.goto("http://localhost:5189/ask");

  await page.getByLabel("سؤالك").fill("When is my flight?");
  await page.getByRole("button", { name: "اسأل البريد", exact: true }).click();
  await page.getByRole("button", { name: /Synthetic trip 0/ }).click();
  await page.getByText("مدعوم من البريد", { exact: true }).waitFor();
  const answer = await page.getByTestId("conversational-answer").innerText();
  assert.match(answer, /(?:20|٢٠).*(?:November|نوفمبر).*(?:2027|٢٠٢٧)/);
  assert.match(answer, /08:15/);
  assert.doesNotMatch(answer, /email_id|chunk_id|2027-11-20T/);
  assert.equal(requests.length, 2);
  assert.equal(requests[1].question, requests[0].question);
  assert.ok(requests[1].email_id > 0);
  assert.equal(
    await page.getByRole("button", { name: /Synthetic trip/ }).count(),
    0,
  );
  console.log(
    "Real clarification click → isolated PostgreSQL /ask → supported answer: PASS",
  );
} finally {
  await browser.close();
}
