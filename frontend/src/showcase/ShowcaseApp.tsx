import { useEffect, useRef, useState } from "react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useSearchParams,
  useLocation,
} from "react-router-dom";
import { z } from "zod";
import { LocaleProvider, useLocale } from "../app/locale";
import { AppBoundary } from "../components/shared/AppBoundary";
import { DesktopTopBar } from "../components/ui/DesktopTopBar";
import { RetroWindow } from "../components/ui/RetroWindow";
import { AskComposer } from "../features/ask/AskComposer";
import "./showcase.css";
import { ModelLab } from "./ModelLab";
import {
  Prediction,
  Answer,
  Collection,
  Tasks,
  request,
  type CollectionEmail,
} from "./api";

export function useRequest<T>() {
  const [data, setData] = useState<T>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function run(path: string, schema: z.ZodType<T>, body?: unknown) {
    if (controller.current) return;
    const active = new AbortController();
    controller.current = active;
    setBusy(true);
    setData(undefined);
    setError("");
    try {
      setData(await request(path, schema, active.signal, body));
    } catch (e) {
      if (!active.signal.aborted)
        setError(e instanceof Error ? e.message : "request");
    } finally {
      controller.current = null;
      setBusy(false);
    }
  }
  return { data, error, busy, run };
}

export function Failure({ code }: { code: string }) {
  const { t } = useLocale();
  if (!code) return null;
  return (
    <p role="alert">
      {code === "model"
        ? t(
            "النموذج غير متاح. يلزم تجهيز الملفات المحلية. لم تُستخدم إجابة جاهزة.",
            "Model unavailable. Provision the local model files; no canned result was substituted.",
          )
        : code === "busy"
          ? t(
              "النموذج مشغول. حاول بعد قليل.",
              "Inference is busy. Please retry shortly.",
            )
          : code === "input"
            ? t(
                "النص طويل أو غير صالح. اختصره ثم أعد المحاولة.",
                "Input is too long or invalid. Shorten it and retry.",
              )
            : t(
                "تعذر إكمال الطلب. حاول مرة أخرى.",
                "The request failed. Please retry.",
              )}
    </p>
  );
}

function Ask() {
  const { t } = useLocale();
  const state = useRequest<z.infer<typeof Answer>>();
  const [question, setQuestion] = useState("");
  return (
    <RetroWindow
      title={t("اسأل البريد", "Ask Mail")}
      bodyClassName="p-4 flex flex-col gap-4"
    >
      <p>
        {t(
          "استرجاع دلالي حقيقي من مجموعة خيالية، مع إجابات مرتبطة بالمصادر.",
          "Real semantic retrieval over an authored collection, with source-linked answers.",
        )}
      </p>
      <div className="flex flex-wrap gap-2">
        {[
          "What is the Atlas workshop date?",
          "ما تاريخ الورشة؟",
          "What meetings do I have this week?",
          "هل عندي مهام متأخرة؟",
          "What is the latest update on ORDER-778?",
        ].map((q) => (
          <button key={q} onClick={() => setQuestion(q)}>
            {q}
          </button>
        ))}
      </div>
      <p className="text-sm">
        {t(
          "استرجاع E5 متعلم، وإجابات استخراجيّة حتمية؛ ليست توليد LLM.",
          "Learned E5 retrieval with deterministic extractive answers, not LLM generation.",
        )}
      </p>
      <AskComposer
        maxLength={1000}
        draft={question}
        onChange={setQuestion}
        busy={state.busy}
        onSubmit={() => {
          if (question.trim())
            void state.run("ask", Answer, {
              question,
              mode: "grounded",
            });
        }}
      />
      <p className="text-sm">
        {t(
          "لا تُحفظ الأسئلة أو تُسجل أو تُرسل لطرف ثالث. استخدم أمثلة خيالية.",
          "Questions are not saved, logged or sent to third parties. Use fictional examples.",
        )}
      </p>
      <Failure code={state.error} />
      {state.data && (
        <section aria-label={t("الإجابة", "Answer")} aria-live="polite">
          <p className="whitespace-pre-wrap" dir="auto">
            {state.data.answer.split(/(\[email_id=\d+\])/g).map((part, i) => {
              const id = /^\[email_id=(\d+)\]$/.exec(part)?.[1];
              return id &&
                state.data!.sources.some(
                  (source) => source.email_id === Number(id),
                ) ? (
                <Link
                  key={i}
                  to={`/collection?email=${id}`}
                  aria-label={`${t("المصدر", "Source")} ${id}`}
                >
                  {part}
                </Link>
              ) : (
                part
              );
            })}
          </p>
          <small>
            {state.data.mode} · {state.data.verification}
          </small>
          {state.data.verification === "not_semantically_verified" && (
            <p>
              {t(
                "قد يخطئ التوليد. تحقق من المصدر؛ صحة الاستشهاد لا تثبت صحة المعنى.",
                "Generation can be wrong. Check the source; valid citations do not verify meaning.",
              )}
            </p>
          )}
          {state.data.sources.map((s) => (
            <article className="surface p-3 my-3" key={s.email_id}>
              <Link to={`/collection?email=${s.email_id}`}>
                {s.subject} — {t("افتح المصدر", "Open source")}
              </Link>
              <blockquote dir="auto" className="whitespace-pre-wrap">
                {s.content}
              </blockquote>
              <small>
                {t(
                  "درجة التشابه، وليست احتمال صحة",
                  "Similarity, not correctness probability",
                )}
                : {s.score.toFixed(3)}
              </small>
            </article>
          ))}
        </section>
      )}
    </RetroWindow>
  );
}

export function Intelligence({ email }: { email: CollectionEmail }) {
  const { t } = useLocale();
  const state = useRequest<z.infer<typeof Prediction>>();
  const [subject, setSubject] = useState(email.subject);
  const [body, setBody] = useState(email.body);
  return (
    <RetroWindow
      title={t("جرّب النموذج", "Inference playground")}
      bodyClassName="p-4 flex flex-col gap-3"
    >
      <p>
        {t(
          "تنبؤ فعلي من النموذج المختار: TF-IDF وانحدار لوجستي. تم تقييمه بالإنجليزية فقط ولم يجتز معيار الجودة الإنتاجية.",
          "Live inference with the selected TF-IDF + logistic regression research model. English validation only; Arabic classification is not evaluated. Not production approved.",
        )}
      </p>
      <label>
        {t("العنوان", "Subject")}
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          maxLength={300}
          dir="auto"
        />
      </label>
      <label>
        {t("النص", "Text")}
        <textarea
          aria-label={t("النص", "Text")}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={6000}
          rows={7}
          dir="auto"
        />
      </label>
      <small>
        {t(
          "استخدم نصاً خيالياً فقط. لا نحفظ المدخلات أو نسجلها أو نستخدمها للتدريب أو نرسلها لأطراف ثالثة.",
          "Use fictional text only. Inputs are not stored, logged, used for training or sent to third parties.",
        )}
      </small>
      <button
        className="primary"
        disabled={state.busy || !body.trim()}
        onClick={() => void state.run("predict", Prediction, { subject, body })}
      >
        {state.busy
          ? t("جارٍ التحليل…", "Analyzing…")
          : t("شغّل التنبؤ", "Run prediction")}
      </button>
      <Failure code={state.error} />
      {state.data && (
        <div aria-label={t("نتيجة التحليل", "Analysis result")}>
          {state.data.predictions.map((p) => (
            <p key={p.category}>
              {p.category} · {t("درجة النموذج", "Model score")}:{" "}
              {p.confidence.toFixed(3)}
            </p>
          ))}
          <p>
            {t(
              "الدرجة الخام ليست احتمال صحة",
              "Raw model score is not a probability of correctness",
            )}
          </p>
          <p>
            {state.data.model_version} · {state.data.processing_ms.toFixed(1)}{" "}
            ms{" "}
            {state.data.cold_load_included &&
              t("(يشمل تحميل النموذج)", "(includes model load)")}
          </p>
          <p>{t("ملخص استخراجي", "Extractive summary")}</p>
          <blockquote dir="auto">{state.data.summary}</blockquote>
        </div>
      )}
    </RetroWindow>
  );
}

function SmartTasks({ email }: { email: CollectionEmail }) {
  const { t } = useLocale();
  const state = useRequest<z.infer<typeof Tasks>>();
  return (
    <RetroWindow
      title={t("المهام الذكية", "Smart Tasks")}
      bodyClassName="p-4 flex flex-col gap-3"
    >
      <p>
        {t(
          "استخراج حقيقي بالقواعد والمواعيد النسبية إلى تاريخ الرسالة. ليس نموذجاً مدرباً.",
          "Live rule-based extraction with deadlines relative to the message date. This is not a trained model.",
        )}
      </p>
      <button
        className="primary"
        disabled={state.busy}
        onClick={() => void state.run(`emails/${email.id}/tasks`, Tasks)}
      >
        {state.busy
          ? t("جارٍ الاستخراج…", "Extracting…")
          : t("استخرج المهام", "Extract tasks")}
      </button>
      <button
        disabled={state.busy}
        onClick={() => void state.run("tasks", Tasks)}
      >
        {t("اعرض مهام المجموعة", "Explore all tasks")}
      </button>
      <p className="text-sm">
        {t(
          "حالة الإنجاز غير معروفة. المواعيد تُقرأ من الرسائل ولا تُفترض.",
          "Completion is unknown. Deadlines come from source messages, never assumptions.",
        )}
      </p>
      <Failure code={state.error} />
      {state.data &&
        (state.data.tasks.length ? (
          state.data.tasks.map((task, i) => (
            <article className="surface p-3" key={i}>
              <p dir="auto">{task.task}</p>
              <p>
                {task.deadline_date ??
                  task.deadline_text ??
                  t("لا يوجد موعد صريح", "No explicit deadline")}
              </p>
              <small>
                {t(
                  "قوة القاعدة وليست احتمالاً",
                  "Rule strength, not probability",
                )}
                : {task.confidence}
              </small>
              <p>
                {t("المسؤول", "Responsible")}:{" "}
                {task.responsible ?? t("غير مذكور", "Not stated")}
              </p>
              <p>
                {t("حالة الموعد", "Deadline state")}:{" "}
                {task.deadline_state === "ambiguous"
                  ? t("غير محسوم", "Ambiguous")
                  : task.deadline_state === "explicit"
                    ? t("مذكور", "Explicit")
                    : t("غير مذكور", "Missing")}
              </p>
              {task.conditional && (
                <p>
                  {t(
                    "طلب مشروط؛ راجع الشرط في المصدر.",
                    "Conditional request; check the source condition.",
                  )}
                </p>
              )}
              {task.state === "superseded" && (
                <p>
                  {t("ألغته رسالة لاحقة.", "Cancelled by a later message.")}{" "}
                  {task.superseded_by?.map((id) => (
                    <Link key={id} to={`/collection?email=${id}`}>
                      #{id}{" "}
                    </Link>
                  ))}
                </p>
              )}
              <Link to={`/collection?email=${task.email_id}`}>
                {t("افتح الرسالة الداعمة", "Open supporting email")}
              </Link>
              <details>
                <summary>{t("المصدر الأصلي", "Original source")}</summary>
                <blockquote className="whitespace-pre-wrap" dir="auto">
                  {task.evidence.text ?? task.evidence.body}
                </blockquote>
              </details>
            </article>
          ))
        ) : (
          <p>
            {t(
              "لم تُستخرج مهام آمنة من هذا النص.",
              "No safe actionable task was extracted.",
            )}
          </p>
        ))}
    </RetroWindow>
  );
}

function Workspace() {
  const { t, language, toggle } = useLocale();
  const [data, setData] = useState<z.infer<typeof Collection>>();
  const [error, setError] = useState("");
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const isLab =
    location.pathname === "/lab" || location.pathname === "/intelligence";
  const [filter, setFilter] = useState("");
  useEffect(() => {
    const c = new AbortController();
    void request("collection", Collection, c.signal)
      .then(setData)
      .catch(() => {
        if (!c.signal.aborted) setError("request");
      });
    return () => c.abort();
  }, []);
  const selected =
    data?.emails.find((e) => e.id === Number(params.get("email"))) ??
    data?.emails[0];
  return (
    <>
      <DesktopTopBar
        language={language === "en" ? "en" : "ar"}
        onToggleLanguage={toggle}
      />
      <main className="max-w-7xl mx-auto p-4 flex flex-col gap-4">
        <div className="page-heading">
          <div>
            <h1>
              {t("هندسة الذكاء الاصطناعي للبريد", "Email AI Engineering")}
            </h1>
            <p>
              {t(
                "استكشف النماذج والاسترجاع والاستخراج. مجموعة مؤلفة خيالية، ونتائج تُحسب عند الطلب.",
                "Explore inference, retrieval and extraction. Authored fictional inputs; results computed on request.",
              )}
            </p>
          </div>
        </div>
        <nav
          className="showcase-nav"
          aria-label={t("أقسام الذكاء الاصطناعي", "AI sections")}
        >
          {(
            [
              ["/", "اسأل البريد", "Ask Mail"],
              ["/tasks", "المهام الذكية", "Smart Tasks"],
              ["/collection", "مجموعة البريد", "Email Collection"],
              ["/lab", "مختبر النماذج", "Model Lab"],
            ] as const
          ).map(([path, ar, en]) => (
            <NavLink
              key={path}
              to={{ pathname: path, search: params.toString() }}
              end
            >
              {t(ar, en)}
            </NavLink>
          ))}
        </nav>
        {data?.metadata && (
          <p className="text-sm">
            {t("تاريخ المجموعة المرجعي", "Collection reference date")}:{" "}
            <bdi>
              {new Date(data.metadata.reference_datetime).toLocaleString(
                language === "ar" ? "ar-SA-u-ca-gregory" : "en-GB",
                { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" },
              )}{" "}
              UTC
            </bdi>{" "}
            ·{" "}
            {t(
              "الأسبوع يبدأ يوم الاثنين. هذه مجموعة خيالية وليست تقويمك الشخصي.",
              "Week starts Monday. This fictional collection is not your personal calendar.",
            )}
          </p>
        )}
        <Failure code={error} />
        {!data && !error && (
          <p role="status">
            {t("جارٍ تحميل المجموعة…", "Loading collection…")}
          </p>
        )}
        {selected && (
          <div
            className={
              isLab
                ? "min-w-0"
                : "grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-4"
            }
          >
            {!isLab && (
              <aside className="min-w-0">
                <RetroWindow
                  title={t("مجموعة البريد", "Email collection")}
                  bodyClassName="p-4 flex flex-col gap-3"
                >
                  <label>
                    {t("اختر مصدراً", "Choose a source")}
                    <select
                      value={selected.id}
                      onChange={(e) => setParams({ email: e.target.value })}
                    >
                      {data!.emails.map((e) => (
                        <option value={e.id} key={e.id}>
                          {e.subject}
                        </option>
                      ))}
                    </select>
                  </label>
                  <h2 dir="auto">{selected.subject}</h2>
                  <small>
                    {selected.sender} · {selected.date.slice(0, 10)}
                  </small>
                  <p dir="auto" className="whitespace-pre-wrap break-words">
                    {selected.body}
                  </p>
                  <small>
                    {t(
                      "أمثلة خيالية بترخيص CC0، وليست بريداً شخصياً أو بيانات تدريب أو معيار جودة ممثلاً.",
                      "CC0 authored examples. Not personal mail, training data or a representative quality benchmark.",
                    )}
                  </small>
                </RetroWindow>
              </aside>
            )}
            <section className="min-w-0">
              <Routes>
                <Route index element={<Ask />} />
                <Route
                  path="tasks"
                  element={<SmartTasks key={selected.id} email={selected} />}
                />
                <Route
                  path="intelligence"
                  element={<ModelLab email={selected} />}
                />
                <Route
                  path="collection"
                  element={
                    <RetroWindow
                      title={t("استكشف المجموعة", "Explore the collection")}
                      bodyClassName="p-4 flex flex-col gap-3"
                    >
                      <p>
                        {t(
                          "٢٤ رسالة مؤلفة باللغتين. اختر رسالة لعرض نصها ومصدرها.",
                          "24 authored bilingual messages. Select a message to inspect its original text.",
                        )}
                      </p>
                      <label>
                        {t("ابحث في المجموعة", "Filter collection")}
                        <input
                          value={filter}
                          onChange={(e) => setFilter(e.target.value)}
                          dir="auto"
                          maxLength={200}
                        />
                      </label>
                      <ul className="collection-list">
                        {data!.emails
                          .filter((e) =>
                            `${e.subject} ${e.body} ${e.sender}`
                              .toLowerCase()
                              .includes(filter.toLowerCase()),
                          )
                          .map((e) => (
                            <li key={e.id}>
                              <Link
                                aria-current={
                                  e.id === selected.id ? "true" : undefined
                                }
                                to={`/collection?email=${e.id}`}
                              >
                                <strong dir="auto">{e.subject}</strong>
                                <small dir="auto">
                                  {e.language.toUpperCase()} ·{" "}
                                  {e.date.slice(0, 10)} · {e.sender}
                                </small>
                              </Link>
                            </li>
                          ))}
                      </ul>
                      {!data!.emails.some((e) =>
                        `${e.subject} ${e.body} ${e.sender}`
                          .toLowerCase()
                          .includes(filter.toLowerCase()),
                      ) && (
                        <p role="status">
                          {t("لا توجد نتائج", "No matching messages")}
                        </p>
                      )}
                    </RetroWindow>
                  }
                />
                <Route path="lab" element={<ModelLab email={selected} />} />
                <Route
                  path="*"
                  element={
                    <Link to="/">
                      {t("العودة إلى اسأل البريد", "Return to Ask Mail")}
                    </Link>
                  }
                />
              </Routes>
            </section>
          </div>
        )}
      </main>
    </>
  );
}

export function ShowcaseApp() {
  return (
    <LocaleProvider>
      <AppBoundary>
        <Workspace />
      </AppBoundary>
    </LocaleProvider>
  );
}
