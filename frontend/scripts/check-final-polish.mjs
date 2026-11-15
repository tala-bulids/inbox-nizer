// Focused frontend acceptance against the existing real model runtime.
// No intercepted requests, substituted outputs, training or resource qualification.
import { chromium } from "playwright";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";

const base = process.env.SHOWCASE_URL || "http://127.0.0.1:4182";
const evidenceDir =
  process.env.SHOWCASE_EVIDENCE_DIR || "../results/final-frontend-polish";
const browser = await chromium.launch({ channel: "msedge", headless: true });
const results = [];
let activePage;
await mkdir(`${evidenceDir}/screenshots`, { recursive: true });
try {
  for (const width of [1440, 390]) {
    const context = await browser.newContext({
      viewport: { width, height: 1000 },
      serviceWorkers: "block",
    });
    const page = await context.newPage();
    activePage = page;
    const errors = [],
      requests = [],
      origins = [],
      screenshots = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (req) => {
      const u = new URL(req.url());
      requests.push(u.pathname);
      origins.push(u.origin);
    });
    const nav = page.getByRole("navigation", {
      name: /Project sections|أقسام المشروع/,
    });
    async function capture(name) {
      await page.evaluate(() => document.fonts.ready);
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
        `overflow: ${width}-${name}`,
      );
      const file = `${width}-${name}.png`;
      await page.screenshot({
        path: `${evidenceDir}/screenshots/${file}`,
        fullPage: true,
      });
      screenshots.push(file);
    }
    async function ask(question, ar = false) {
      await page
        .getByLabel(ar ? "سؤالك" : "Your question", { exact: true })
        .fill(question);
      const response = page.waitForResponse(
        (r) => r.url().endsWith("/showcase/ask"),
        { timeout: 120000 },
      );
      await page
        .getByRole("button", { name: ar ? "اسأل" : "Ask", exact: true })
        .click();
      const r = await response;
      assert.equal(r.status(), 200);
      await page
        .getByRole("region", { name: ar ? "الإجابة" : "Answer", exact: true })
        .waitFor();
      return r.json();
    }
    assert.equal((await page.goto(base)).status(), 200);
    await page
      .getByRole("heading", { name: "Inbox-nizer", exact: true })
      .waitFor();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
    await capture("home-ar");
    await page.getByRole("button", { name: "Switch to English" }).click();
    await capture("home-en");
    await page.getByRole("link", { name: "Try the project" }).click();
    await page.getByLabel("Choose a source").waitFor();
    assert.deepEqual(await nav.getByRole("link").allTextContents(), [
      "Home",
      "Ask Mail",
      "Smart Tasks",
      "Email Collection",
      "Model Lab",
    ]);
    const original = await ask("What is the Atlas workshop date?");
    assert.equal(original.status, "answered");
    assert(original.answer.includes("2026-11-05"));
    await page
      .getByRole("link", { name: "Source 1", exact: true })
      .first()
      .click();
    assert.equal(await page.getByLabel("Choose a source").inputValue(), "1");
    await nav.getByRole("link", { name: "Ask Mail" }).click();
    const novel = await ask("Could you show the latest update on ORDER-778?");
    assert.equal(novel.status, "answered");
    assert(novel.sources.some((s) => s.email_id === 18));
    await page
      .getByRole("region", { name: "Supporting messages" })
      .locator("summary")
      .first()
      .click();
    await capture("ask-en");
    const unknown = await ask("What is my bank account password?");
    assert.equal(unknown.status, "insufficient_evidence");
    await page
      .getByText(
        "I couldn't find enough information in the messages to answer this question.",
      )
      .waitFor();
    await nav.getByRole("link", { name: "Smart Tasks" }).click();
    await page
      .getByRole("heading", { name: "Smart Tasks", exact: true })
      .waitFor();
    await page.getByLabel("Choose a source").selectOption("7");
    await page
      .getByRole("button", { name: "Extract tasks", exact: true })
      .click();
    await page.getByText("Maya", { exact: true }).waitFor();
    await page.getByText("Original source", { exact: true }).click();
    await capture("tasks-en");
    await page.getByRole("link", { name: "Open supporting email" }).click();
    assert.equal(await page.getByLabel("Choose a source").inputValue(), "7");
    await page.getByLabel("Filter collection").fill("ORDER-778");
    assert((await page.locator(".collection-list li").count()) >= 1);
    await capture("collection-en");
    await nav.getByRole("link", { name: "Model Lab" }).click();
    await page
      .getByRole("heading", { name: "The idea", exact: true })
      .waitFor();
    const evidence = await (
      await context.request.get(`${base}/api/showcase/portfolio`)
    ).json();
    assert.equal(evidence.serving_runtime.id, "e5-int8-fp32-corpus-v1");
    await capture("lab-en");
    await page.getByRole("button", { name: "Training & data" }).click();
    await page.getByText("Training details & reproducibility").click();
    assert(
      await page
        .getByText(
          evidence.models[0].history.train_unweighted_binary_log_loss.toFixed(
            4,
          ),
          { exact: true },
        )
        .isVisible(),
    );
    const reproduction = await context.request.get(
      `${base}/api/showcase/reproduction`,
    );
    assert.equal(reproduction.status(), 200);
    assert((await reproduction.text()).includes("python -m ml_phase2.run"));
    await page.getByText("Training details & reproducibility").click();
    await capture("training-en");
    await page.getByRole("button", { name: "Evaluation", exact: true }).click();
    assert(
      await page
        .getByRole("region", { name: "Classifier comparison" })
        .getByText(
          `${(evidence.models[0].metrics.top1_accuracy * 100).toFixed(1)}%`,
          { exact: true },
        )
        .isVisible(),
    );
    await capture("evaluation-en");
    await page.getByText("Detailed metrics & errors").click();
    await page.getByLabel("Inspect experiment").selectOption("C");
    await page.getByText("Confusion matrix", { exact: true }).click();
    await page.getByRole("region", { name: "Confusion table" }).waitFor();
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.getByLabel("Inspect experiment").selectOption("B");
    await page.getByText(/Historical result excluded from selection/).waitFor();
    await page.getByRole("button", { name: "Playground", exact: true }).click();
    await page
      .getByLabel("Subject", { exact: true })
      .fill("Fictional interview invitation");
    await page
      .getByLabel("Text", { exact: true })
      .fill(
        "Thank you for applying for the research position. We would like to invite you to an interview next Tuesday.",
      );
    const predictionResponse = page.waitForResponse((r) =>
      r.url().endsWith("/showcase/predict"),
    );
    await page.getByRole("button", { name: "Run prediction" }).click();
    const prediction = await predictionResponse;
    assert.equal(prediction.status(), 200);
    const predicted = await prediction.json();
    assert.equal(predicted.model_version, "phase2-A");
    assert.equal(
      predicted.artifact_sha256,
      evidence.models[0].run.artifact_sha256,
    );
    assert(predicted.processing_ms > 0);
    await page.getByLabel("Analysis result").waitFor();
    await capture("prediction-en");
    await page.getByRole("button", { name: "التبديل للعربية" }).click();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
    await page.getByText("طلبات توظيف", { exact: true }).waitFor();
    await capture("prediction-ar");
    await page.getByRole("button", { name: "فكرة العمل", exact: true }).click();
    await capture("lab-ar");
    await page
      .getByRole("button", { name: "البيانات والتدريب", exact: true })
      .click();
    await capture("training-ar");
    await page
      .getByRole("button", { name: "نتائج التجارب", exact: true })
      .click();
    await capture("evaluation-ar");
    await nav.getByRole("link", { name: "المهام", exact: true }).click();
    await page.getByRole("heading", { name: "المهام", exact: true }).waitFor();
    await page.getByLabel("اختر رسالة").selectOption("14");
    await page
      .getByRole("button", { name: "استخرج المهام", exact: true })
      .click();
    await page.getByText("ليلى", { exact: true }).waitFor();
    await page.getByText("غير مذكور في الرسالة", { exact: true }).waitFor();
    await page.getByText("الرسالة الأصلية", { exact: true }).click();
    await capture("tasks-ar");
    assert.equal((await page.reload()).status(), 200);
    assert.equal(await page.getByLabel("اختر رسالة").inputValue(), "14");
    await nav.getByRole("link", { name: "اسأل البريد", exact: true }).click();
    const arabic = await ask("هل عندي مهام متأخرة؟", true);
    assert.equal(arabic.status, "answered");
    await capture("ask-ar");
    await nav.getByRole("link", { name: "الرسائل", exact: true }).click();
    await capture("collection-ar");
    for (const route of [
      "/ask",
      "/collection?email=18",
      "/lab",
      "/intelligence?email=7",
      "/tasks?email=7",
    ]) {
      assert.equal((await page.goto(base + route)).status(), 200);
      await nav.getByRole("link", { name: "الرسائل", exact: true }).waitFor();
      assert.equal((await page.reload()).status(), 200);
      if (route.startsWith("/lab") || route.startsWith("/intelligence"))
        await page
          .getByRole("heading", { name: "فكرة العمل", exact: true })
          .waitFor();
      else await page.getByLabel("اختر رسالة").waitFor();
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
    }
    const visibleText = await page.locator("main").innerText();
    assert(
      !/Collection reference date|تاريخ المجموعة المرجعي|e5-int8-fp32-corpus-v1/.test(
        visibleText,
      ),
    );
    assert(origins.every((origin) => origin === new URL(base).origin));
    assert.deepEqual(errors, []);
    assert.equal((await context.cookies()).length, 0);
    assert.equal(
      await page.evaluate(() => localStorage.length + sessionStorage.length),
      0,
    );
    assert(
      !requests.some(
        (path) =>
          path.startsWith("/api/") && !path.startsWith("/api/showcase/"),
      ),
    );
    results.push({
      width,
      locales: ["ar", "en"],
      realInference: true,
      runtime: evidence.serving_runtime.id,
      originalQuestion: original.status,
      novelQuestion: novel.status,
      missingEvidence: unknown.status,
      arabicQuestion: arabic.status,
      tasksAndCitations: true,
      metricsMatchSavedEvidence: true,
      confusionMatrix: true,
      deepLinksAndRefresh: true,
      noHorizontalOverflow: true,
      pageErrors: 0,
      privateApiRequests: 0,
      thirdPartyBrowserRequests: 0,
      cookies: 0,
      browserStorageEntries: 0,
      prediction: {
        model: predicted.model_version,
        sha256: predicted.artifact_sha256,
        category: predicted.predictions[0].category,
        score: predicted.predictions[0].confidence,
      },
      screenshots,
    });
    await context.close();
  }
} catch (error) {
  if (activePage && !activePage.isClosed()) {
    await activePage.screenshot({
      path: `${evidenceDir}/failure.png`,
      fullPage: true,
    });
    console.error({
      url: activePage.url(),
      visibleText: await activePage.locator("main").innerText(),
    });
  }
  throw error;
} finally {
  await browser.close();
}
const report = {
  scope:
    "Frontend acceptance with existing real models; no retraining or memory qualification",
  base,
  completedAt: new Date().toISOString(),
  results,
};
await writeFile(
  `${evidenceDir}/browser-verification.json`,
  JSON.stringify(report, null, 2),
);
console.log(JSON.stringify(report, null, 2));
