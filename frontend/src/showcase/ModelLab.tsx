import { useEffect, useState } from "react";
import { z } from "zod";
import { useLocale } from "../app/locale";
import { RetroWindow } from "../components/ui/RetroWindow";
import { Portfolio, request, type CollectionEmail } from "./api";
import { Failure, Intelligence } from "./ShowcaseApp";
const names: Record<string, string> = {
  A: "TF-IDF + Logistic Regression",
  B: "DistilBERT · checkpoint-3159",
  C: "Frozen multilingual E5 + Linear Head",
};
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
export function ModelLab({ email }: { email: CollectionEmail }) {
  const { t } = useLocale();
  const [data, setData] = useState<z.infer<typeof Portfolio>>();
  const [error, setError] = useState("");
  const [candidate, setCandidate] = useState("A");
  const [section, setSection] = useState("overview");
  useEffect(() => {
    const c = new AbortController();
    void request("portfolio", Portfolio, c.signal)
      .then(setData)
      .catch(() => {
        if (!c.signal.aborted) setError("request");
      });
    return () => c.abort();
  }, []);
  const model = data?.models.find((m) => m.id === candidate);
  const labels = model ? Object.keys(model.metrics.per_class) : [];
  return (
    <RetroWindow
      title={t("مختبر النماذج", "Model Lab")}
      bodyClassName="lab-layout p-4 flex flex-col gap-4"
    >
      <div className="lab-intro">
        <span className="lab-kicker">INBOX-NIZER / RESEARCH NOTES</span>
        <h2>{t("من التجربة إلى الاستدلال", "From experiment to inference")}</h2>
        <p>
          {t(
            "ثلاث مقاربات، وقرار قائم على الأدلة. استكشف النتائج والقيود ثم جرّب النموذج بنفسك.",
            "Three approaches, one evidence-based decision. Inspect the results and limitations, then try the model yourself.",
          )}
        </p>
      </div>
      <div
        className="lab-tabs"
        role="group"
        aria-label={t("أقسام المختبر", "Lab sections")}
      >
        {(
          [
            ["overview", "النماذج", "Models"],
            ["training", "التدريب والبيانات", "Training & data"],
            ["evaluation", "التقييم", "Evaluation"],
            ["playground", "جرّب النموذج", "Playground"],
          ] as const
        ).map(([id, ar, en]) => (
          <button
            key={id}
            aria-pressed={section === id}
            onClick={() => setSection(id)}
          >
            {t(ar, en)}
          </button>
        ))}
      </div>
      <Failure code={error} />
      {!data && !error && (
        <p role="status">{t("جارٍ تحميل الأدلة…", "Loading evidence…")}</p>
      )}
      {data && model && (
        <>
          <p className="lab-notice">
            {t(
              "نموذج بحثي غير معتمد للإنتاج. نتائج التصنيف من تحقق إنجليزي مستهلك؛ ليست دقة عامة أو اختباراً نهائياً.",
              "Research model, not production approved. Classification results are consumed English validation evidence, not general accuracy or final test scores.",
            )}
          </p>
          {section === "overview" && (
            <>
              <div className="lab-models">
                {data.models.map((m) => (
                  <article className="surface p-4" key={m.id}>
                    <span className="lab-kicker">
                      {m.id === data.selected
                        ? t("النموذج المختار", "SELECTED RESEARCH MODEL")
                        : m.id === "B"
                          ? t("تاريخي · مستبعد", "HISTORICAL · EXCLUDED")
                          : t("مرشح متعدد اللغات", "MULTILINGUAL CANDIDATE")}
                    </span>
                    <h3>{names[m.id]}</h3>
                    <p>
                      Macro F1:{" "}
                      <strong>{m.metrics.top1_macro_f1.toFixed(3)}</strong>
                    </p>
                    <meter
                      aria-label={`${m.id} macro F1`}
                      min={0}
                      max={1}
                      value={m.metrics.top1_macro_f1}
                    />
                    <p>
                      p95 {m.run.benchmark.p95_ms.toFixed(1)} ms ·{" "}
                      {m.run.benchmark.process_peak_wset_mib.toFixed(0)} MiB
                    </p>
                    <small>
                      {t(
                        "قياس Windows محلي، وليس سعة Render.",
                        "Local Windows measurement, not Render capacity.",
                      )}
                    </small>
                  </article>
                ))}
              </div>
              <h3>{t("لماذا النموذج A؟", "Why candidate A?")}</h3>
              <p>
                {t(
                  "تفوق A على C في F1 وسرعة الاستدلال مع ذاكرة أقل. استُبعد DistilBERT لاحتمال تعرضه لبيانات التحقق سابقاً. المشفر E5 في C مجمد؛ لم يُنفذ ضبط محول جديد.",
                  "A outperformed C on macro F1 and latency with lower memory use. DistilBERT was excluded because it may have seen this corpus before. C uses frozen E5; no new transformer fine-tuning was executed.",
                )}
              </p>
              <p>
                {t(
                  "التصنيف: تحقق إنجليزي فقط. الاسترجاع: E5 متعدد اللغات. المهام: قواعد عربية وإنجليزية وليست نموذجاً مدرباً.",
                  "Classification: English validation only. Retrieval: multilingual E5. Tasks: Arabic/English rules, not a trained task model.",
                )}
              </p>
              <details>
                <summary>
                  {t(
                    "إصدارات النماذج وبصمات الملفات",
                    "Model versions & artifact identity",
                  )}
                </summary>
                {data.models.map((m) => (
                  <div key={m.id} className="my-3">
                    <strong>{names[m.id]}</strong>
                    <pre>{JSON.stringify(m.run.identity, null, 2)}</pre>
                    <code className="break-all">
                      {m.run.artifact_sha256 ??
                        t(
                          "بصمة الأوزان الأصلية أعلاه",
                          "Source weight hash above",
                        )}
                    </code>
                  </div>
                ))}
              </details>
              <h3>{t("الاسترجاع والمهام", "Retrieval & tasks")}</h3>
              <p>
                {data.rag.qa.n} {t("سؤالاً مؤلفاً", "authored questions")} ·
                Recall@5 {pct(data.rag.qa.retrieval["recall@5"])} ·{" "}
                {data.rag.memory_mib.toFixed(0)} MiB
              </p>
              <p>
                {t(
                  "اختبارات مؤلفة بواسطة نفس المساعد، وليست تقييماً بشرياً مستقلاً. توجد حالتا إخفاق في أدلة الإجابة. الإجابات استخراجيّة وليست توليد LLM. الذاكرة المقاسة تتجاوز Render Free.",
                  "Probes share the implementation’s AI author; they are not independent human evaluation. Two answer-evidence failures remain. Answers are extractive, not LLM generation. Measured retrieval memory exceeds Render Free.",
                )}
              </p>
            </>
          )}
          {section === "training" && (
            <>
              <h3>{t("البيانات والمنهجية", "Data & methodology")}</h3>
              <p dir="auto">
                {data.dataset.source.repository} · {data.dataset.source.license}
              </p>
              <p>
                {t(
                  "تصريح الناشر MIT مع كود توليد اصطناعي؛ منشأ كل صف غير مثبت. لا نعيد نشر النصوص الخام.",
                  "Publisher-declared MIT with synthetic generation code; individual row provenance is not verified. Raw texts are not redistributed.",
                )}
              </p>
              <div className="lab-stats">
                {Object.entries(data.dataset.splits).map(([name, split]) => (
                  <div className="surface p-3" key={name}>
                    <small>
                      {name === "train"
                        ? t("تدريب", "Train")
                        : name === "validation"
                          ? t("تحقق", "Validation")
                          : t(
                              "اختبار محجوز · غير مقيّم",
                              "Reserved test · not evaluated",
                            )}
                    </small>
                    <strong>{split.rows}</strong>
                  </div>
                ))}
              </div>
              <p>
                {t("بذرة", "Seed")} {data.dataset.seed} · {data.dataset.groups}{" "}
                {t("مجموعة قوالب", "template groups")} ·{" "}
                {data.dataset.near_duplicate_pairs}{" "}
                {t("زوجاً شبه مكرر", "near-duplicate pairs")}
              </p>
              <p>
                {t(
                  "تطبيع NFC وتنظيف HTML وحجب البريد والروابط والأرقام الطويلة. دمج التكرار وعزل الوسوم المتناقضة وتجميع القوالب بتشابه 0.9 قبل التقسيم. لا توجد بيانات مرسل أو محادثة؛ لا يمكن استبعاد التسرب. استُخدمت المجموعة تاريخياً، والاختبار المحجوز ليس اختبار إصدار مستقلاً.",
                  "NFC normalization, HTML cleaning and contact/URL/long-number redaction. Exact deduplication, contradictory-label quarantine and template grouping at cosine 0.9 precede splitting. No sender/thread metadata; leakage cannot be eliminated. The historically used corpus cannot supply a new independent release holdout.",
                )}
              </p>
              <div className="lab-two">
                <div>
                  <h3>
                    {t(
                      "توزيع الفئات (متعددة الوسوم)",
                      "Class distribution (multi-label)",
                    )}
                  </h3>
                  {Object.entries(data.dataset.class_counts).map(
                    ([name, count]) => (
                      <div className="lab-bar" key={name}>
                        <span>{name}</span>
                        <meter
                          aria-label={name}
                          min={0}
                          max={data.dataset.usable_rows}
                          value={count}
                        />
                        <span>{count}</span>
                      </div>
                    ),
                  )}
                </div>
                <div>
                  <h3>
                    {t("إعدادات التدريب المنفذ", "Executed training settings")}
                  </h3>
                  <dl>
                    {Object.entries({
                      ...data.configuration.linear,
                      ...data.configuration.tfidf,
                    }).map(([key, value]) => (
                      <div key={key}>
                        <dt>{key}</dt>
                        <dd>{String(value)}</dd>
                      </div>
                    ))}
                  </dl>
                  <p>
                    {t(
                      "اللغة: إنجليزية فقط. العربية: غير مقيّمة.",
                      "Language: English only. Arabic: Not evaluated.",
                    )}
                  </p>
                </div>
              </div>
              <h3>
                {t(
                  "خسارة التدريب والتحقق النهائية",
                  "Final training & validation loss",
                )}
              </h3>
              <p>
                {t(
                  "منحنيات العصور: غير متاحة. نُفذ تدريب خطي مرة واحدة، ولم يُحفظ تاريخ خسارة عبر العصور.",
                  "Epoch loss curves: Not available. One fixed linear fit was executed; no epoch-by-epoch loss history was saved.",
                )}
              </p>
              <div
                className="lab-table"
                tabIndex={0}
                role="region"
                aria-label={t("خسارة التدريب", "Training loss")}
              >
                <table>
                  <caption>
                    {t(
                      "الخسارة الثنائية اللوغاريتمية غير الموزونة",
                      "Unweighted binary log loss",
                    )}
                  </caption>
                  <thead>
                    <tr>
                      <th>{t("النموذج", "Model")}</th>
                      <th>{t("التدريب", "Train")}</th>
                      <th>{t("التحقق", "Validation")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.models.map((m) => (
                      <tr key={m.id}>
                        <th>{names[m.id]}</th>
                        <td>
                          {m.history.train_unweighted_binary_log_loss?.toFixed(
                            4,
                          ) ?? t("غير متاح", "Not available")}
                        </td>
                        <td>
                          {m.history.validation_unweighted_binary_log_loss?.toFixed(
                            4,
                          ) ?? t("غير متاح", "Not available")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <details>
                <summary>
                  {t("إعادة تنفيذ التجربة", "Reproduce the experiment")}
                </summary>
                <p>
                  {t(
                    "التدريب محلي فقط، ولا يُنفذ بالنقر هنا. الإعدادات والأوامر الكاملة في المستودع.",
                    "Training runs locally, not on website clicks. Full commands and configuration are in the repository.",
                  )}
                </p>
                <code>python -m ml_phase2.run --help</code>
                <p>
                  <a
                    href="/api/showcase/reproduction"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t(
                      "المنهجية وملفات الأدلة",
                      "Methodology & evidence files",
                    )}
                  </a>
                </p>
              </details>
            </>
          )}
          {section === "evaluation" && (
            <>
              <label>
                {t("التجربة المعروضة", "Inspect experiment")}
                <select
                  value={candidate}
                  onChange={(e) => setCandidate(e.target.value)}
                >
                  {data.models.map((m) => (
                    <option value={m.id} key={m.id}>
                      {m.id}: {names[m.id]}
                    </option>
                  ))}
                </select>
              </label>
              {candidate === "B" && (
                <p className="lab-notice">
                  {t(
                    "مستبعد: احتمال تداخل التدريب التاريخي مع التحقق.",
                    "Excluded: unknown historical training overlap with validation data.",
                  )}
                </p>
              )}
              <div className="lab-stats">
                {[
                  [
                    t("دقة أعلى تصنيف", "Top-1 accuracy"),
                    pct(model.metrics.top1_accuracy),
                  ],
                  ["Macro F1", model.metrics.top1_macro_f1.toFixed(3)],
                  ["Weighted F1", model.metrics.top1_weighted_f1.toFixed(3)],
                ].map(([label, value]) => (
                  <div className="surface p-3" key={label}>
                    <small>{label}</small>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
              <p>
                n={model.metrics.n} ·{" "}
                {t(
                  "تحقق إنجليزي. الدقة تقبل أي وسم مرجعي، وF1 تقارن التنبؤ الواحد بكل الوسوم؛ لذلك تختلف المقاييس.",
                  "English validation. Accuracy accepts any gold label; F1 compares the single prediction to all gold labels, so these metrics differ.",
                )}
              </p>
              <div
                className="lab-table"
                tabIndex={0}
                role="region"
                aria-label={t("أداء الفئات", "Per-class performance")}
              >
                <table>
                  <caption>{t("أداء الفئات", "Per-class performance")}</caption>
                  <thead>
                    <tr>
                      <th>{t("الفئة", "Category")}</th>
                      <th>Precision</th>
                      <th>Recall</th>
                      <th>F1</th>
                      <th>Support</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(model.metrics.per_class).map(
                      ([name, s]) => (
                        <tr key={name}>
                          <th>{name}</th>
                          <td>{s.precision.toFixed(3)}</td>
                          <td>{s.recall.toFixed(3)}</td>
                          <td>{s.f1.toFixed(3)}</td>
                          <td>{s.support}</td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
              <details>
                <summary>{t("مصفوفة الالتباس", "Confusion matrix")}</summary>
                <p>
                  {t(
                    "الصفوف مرجعية والأعمدة متوقعة؛ الوزن 1/عدد الوسوم، لذلك الأعداد كسرية. اسحب أفقياً لعرض الفئات.",
                    "Rows are gold, columns predicted; weight is 1/label-count, so counts are fractional. Scroll horizontally for all categories.",
                  )}
                </p>
                <div
                  className="lab-table"
                  tabIndex={0}
                  role="region"
                  aria-label={t("جدول الالتباس", "Confusion table")}
                >
                  <table>
                    <caption>{names[candidate]}</caption>
                    <thead>
                      <tr>
                        <th>{t("مرجع / تنبؤ", "Gold / predicted")}</th>
                        {labels.map((l) => (
                          <th key={l}>{l}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {model.metrics.confusion_matrix.map((row, i) => (
                        <tr key={labels[i]}>
                          <th>{labels[i]}</th>
                          {row.map((v, j) => (
                            <td
                              className={i === j ? "matrix-diagonal" : ""}
                              key={j}
                            >
                              {v.toFixed(1)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
              <h3>{t("المعايرة وأنماط الخطأ", "Calibration & errors")}</h3>
              <p>
                ECE {model.metrics.top1_ece.toFixed(4)} ·{" "}
                {model.metrics.wrong_confident_ge_080}{" "}
                {t(
                  "خطأ بدرجة ≥ 0.8. الدرجات غير معايرة وليست احتمال صحة.",
                  "errors with score ≥ 0.8. Scores are uncalibrated, not correctness probabilities.",
                )}
              </p>
              <ul>
                {Object.entries(model.metrics.error_patterns)
                  .slice(0, 5)
                  .map(([name, n]) => (
                    <li key={name} dir="auto">
                      {name}: {n}
                    </li>
                  ))}
              </ul>
              <p>
                {t(
                  "أمثلة معاد صياغتها: نشرة خصم صُنفت ترويجاً، وإشعار تأخر طلب صُنف دعماً مقابل مرجع مالي. التباس محتمل في الوسوم؛ لم نغيرها لتحسين النتائج.",
                  "Paraphrased errors: a discount newsletter predicted as Promotions; an order-delay notice predicted as Support against a Finance reference. Possible label ambiguity; no labels were changed to improve scores.",
                )}
              </p>
              <h3>
                {t("حدود اللغة ومعيار الجودة", "Language gaps & quality gate")}
              </h3>
              <p>
                {t(
                  "العربية للنموذج المختار: غير مقيّمة. الاختبار النهائي: غير مقيّم.",
                  "Selected model Arabic: Not evaluated. Final test: Not evaluated.",
                )}
              </p>
              <p>
                {t(
                  "فشل معيار الجودة التاريخي لـ DistilBERT. تشخيص تطويري مستهلك وليس دقة ممثلة:",
                  "Historical DistilBERT quality gate FAILED. Consumed development diagnostics, not representative accuracy:",
                )}{" "}
                {Math.round(
                  data.historical.development.top1_accuracy *
                    data.historical.development.n,
                )}
                /{data.historical.development.n} · macro F1{" "}
                {data.historical.development.top1_macro_f1.toFixed(4)}
              </p>
              <ul>
                {Object.entries(data.historical.languages).map(([name, s]) => (
                  <li key={name}>
                    {name}: {s.correct}/{s.n}
                  </li>
                ))}
              </ul>
              <p>
                {t(
                  "عينات صغيرة وتصنيف لغوي استدلالي. يلزم تقييم مستقل بمراجعة بشرية قبل اعتماد الإنتاج.",
                  "Small slices with heuristic language labels. Independent human-reviewed evaluation is required before production approval.",
                )}
              </p>
            </>
          )}
          {section === "playground" && (
            <Intelligence key={email.id} email={email} />
          )}
          <small className="break-all">
            {t("نسخة الأدلة", "Evidence version")}: {data.evidence_version}
          </small>
        </>
      )}
    </RetroWindow>
  );
}
