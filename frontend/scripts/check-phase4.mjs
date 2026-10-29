// Real loopback integration. No network interception or substituted model output.
import { chromium } from "playwright";
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
const base = process.env.SHOWCASE_URL || "http://127.0.0.1:4181";
const evidenceDir = process.env.SHOWCASE_EVIDENCE_DIR || "../docs/phase4";
const output = `${evidenceDir}/screenshots`;
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
      requests = [],
      origins = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on(
      "request",
      (request) => (
        requests.push(new URL(request.url()).pathname),
        origins.push(new URL(request.url()).origin)
      ),
    );
    await page.goto(base);
    await page.getByRole("button", { name: "Switch to English" }).click();
    await page.getByLabel("Choose a source").waitFor();
    const nav = page.getByRole("navigation", { name: "AI sections" });
    assert.deepEqual(await nav.getByRole("link").allTextContents(), [
      "Ask Mail",
      "Smart Tasks",
      "Email Collection",
      "Model Lab",
    ]);
    async function ask(question) {
      await page.getByLabel("Your question").fill(question);
      const response = page.waitForResponse(
        (r) => r.url().endsWith("/showcase/ask"),
        { timeout: 120000 },
      );
      await page.getByRole("button", { name: "Ask AI", exact: true }).click();
      const r = await response;
      assert.equal(r.status(), 200);
      await page.getByRole("region", { name: "Answer", exact: true }).waitFor();
      return r.json();
    }
    const original = await ask("What is the Atlas workshop date?");
    assert.equal(original.status, "answered");
    assert(original.answer.includes("2026-11-05"));
    await page
      .getByRole("link", { name: "Source 1", exact: true })
      .first()
      .click();
    assert.equal(await page.getByLabel("Choose a source").inputValue(), "1");
    await nav.getByRole("link", { name: "Ask Mail", exact: true }).click();
    const custom = await ask("Could you show the latest update on ORDER-778?");
    assert.equal(custom.status, "answered");
    assert(custom.sources.some((s) => s.email_id === 18));
    await page.screenshot({
      path: `${output}/${width}-ask-en.png`,
      fullPage: true,
    });
    const unknown = await ask("What is my bank account password?");
    assert.equal(unknown.status, "insufficient_evidence");
    await nav.getByRole("link", { name: "Smart Tasks", exact: true }).click();
    await page.getByLabel("Choose a source").selectOption("7");
    await page
      .getByRole("button", { name: "Extract tasks", exact: true })
      .click();
    await page.getByText("Responsible: Maya", { exact: true }).waitFor();
    await page.getByText("Deadline state: Explicit", { exact: true }).waitFor();
    await page.getByText("Original source", { exact: true }).click();
    await page
      .getByRole("link", { name: "Open supporting email", exact: true })
      .click();
    assert.equal(await page.getByLabel("Choose a source").inputValue(), "7");
    await page.getByLabel("Filter collection").fill("ORDER-778");
    assert((await page.locator(".collection-list li").count()) >= 1);
    await nav.getByRole("link", { name: "Model Lab", exact: true }).click();
    await page.getByText("Why candidate A?", { exact: true }).waitFor();
    const evidence = await (
      await context.request.get(`${base}/api/showcase/portfolio`)
    ).json();
    await page.screenshot({
      path: `${output}/${width}-lab-en.png`,
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Training & data", exact: true })
      .click();
    await page.getByText(/Epoch loss curves: Not available/).waitFor();
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
    await page.getByText("Reproduce the experiment", { exact: true }).click();
    const reproduction = await context.request.get(
      `${base}/api/showcase/reproduction`,
    );
    assert.equal(reproduction.status(), 200);
    assert((await reproduction.text()).includes("python -m ml_phase2.run"));
    await page.getByRole("button", { name: "Evaluation", exact: true }).click();
    assert(
      await page
        .getByText(
          `${(evidence.models[0].metrics.top1_accuracy * 100).toFixed(1)}%`,
          { exact: true },
        )
        .isVisible(),
    );
    await page.getByLabel("Inspect experiment").selectOption("C");
    assert(await page.getByText("83.7%", { exact: true }).isVisible());
    await page.getByText("Confusion matrix", { exact: true }).click();
    await page
      .getByRole("region", { name: "Confusion table", exact: true })
      .waitFor();
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: `${output}/${width}-evaluation-en.png`,
      fullPage: true,
    });
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
    await page
      .getByRole("button", { name: "Run prediction", exact: true })
      .click();
    const prediction = await predictionResponse;
    assert.equal(prediction.status(), 200);
    const predicted = await prediction.json();
    assert.equal(predicted.model_version, "phase2-A");
    assert.equal(
      predicted.artifact_sha256,
      evidence.models[0].run.artifact_sha256,
    );
    assert(predicted.processing_ms > 0);
    await page.getByLabel("Analysis result", { exact: true }).waitFor();
    await page.screenshot({
      path: `${output}/${width}-prediction-en.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "التبديل للعربية" }).click();
    await page.getByRole("button", { name: "التقييم", exact: true }).click();
    await page.getByText(/العربية للنموذج المختار: غير مقيّمة/).waitFor();
    assert.equal(await page.locator("html").getAttribute("dir"), "rtl");
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    await page.screenshot({
      path: `${output}/${width}-evaluation-ar.png`,
      fullPage: true,
    });
    await page
      .getByRole("link", { name: "المهام الذكية", exact: true })
      .click();
    await page.getByLabel("اختر مصدراً").selectOption("14");
    await page
      .getByRole("button", { name: "استخرج المهام", exact: true })
      .click();
    await page.getByText("المسؤول: ليلى", { exact: true }).waitFor();
    await page.getByText("حالة الموعد: غير مذكور", { exact: true }).waitFor();
    await page.getByText("المصدر الأصلي", { exact: true }).click();
    await page.screenshot({
      path: `${output}/${width}-tasks-ar.png`,
      fullPage: true,
    });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    );
    assert.equal((await page.reload()).status(), 200);
    assert.equal(await page.getByLabel("اختر مصدراً").inputValue(), "14");
    await page.getByRole("link", { name: "اسأل البريد", exact: true }).click();
    await page.getByLabel("سؤالك").fill("هل عندي مهام متأخرة؟");
    const arabicResponse = page.waitForResponse((r) =>
      r.url().endsWith("/showcase/ask"),
    );
    await page
      .getByRole("button", { name: "اسأل البريد", exact: true })
      .click();
    const arabic = await (await arabicResponse).json();
    assert.equal(arabic.status, "answered");
    await page.getByRole("region", { name: "الإجابة", exact: true }).waitFor();
    await page.screenshot({
      path: `${output}/${width}-ask-ar.png`,
      fullPage: true,
    });
    for (const route of [
      "/collection?email=18",
      "/lab",
      "/intelligence?email=7",
    ]) {
      assert.equal((await page.goto(base + route)).status(), 200);
      await page
        .getByRole("link", { name: "مجموعة البريد", exact: true })
        .waitFor();
      assert.equal((await page.reload()).status(), 200);
      if (route.startsWith("/collection"))
        assert.equal(await page.getByLabel("اختر مصدراً").inputValue(), "18");
      else
        await page
          .getByText("من التجربة إلى الاستدلال", { exact: true })
          .waitFor();
    }
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
      realInference: true,
      originalQuestion: original.status,
      novelQuestion: custom.status,
      missingEvidence: unknown.status,
      arabicQuestion: arabic.status,
      tasksAndCitations: true,
      sourceRefresh: true,
      deepLinks: true,
      reproductionLink: true,
      thirdPartyBrowserRequests: 0,
      metricsMatchSavedEvidence: true,
      confusionMatrix: true,
      selectedPrediction: {
        model: predicted.model_version,
        sha256: predicted.artifact_sha256,
        category: predicted.predictions[0].category,
        score: predicted.predictions[0].confidence,
        processing_ms: predicted.processing_ms,
        cold_load_included: predicted.cold_load_included,
      },
      rtl: true,
      noHorizontalOverflow: true,
      pageErrors: 0,
      cookies: 0,
      browserStorageEntries: 0,
      privateApiRequests: 0,
    });
    await context.close();
  }
} finally {
  await browser.close();
}
await writeFile(
  `${evidenceDir}/browser-verification.json`,
  JSON.stringify(
    {
      scope:
        "Real local offline E5 and selected Phase 2 A classifier. Interaction evidence, not model quality evaluation.",
      results,
    },
    null,
    2,
  ),
);
console.log(JSON.stringify(results, null, 2));
