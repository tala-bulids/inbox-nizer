import { useEffect, useRef, useState } from "react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useSearchParams,
} from "react-router-dom";
import { z } from "zod";
import { LocaleProvider, useLocale } from "../app/locale";
import { AppBoundary } from "../components/shared/AppBoundary";
import { DesktopTopBar } from "../components/ui/DesktopTopBar";
import { RetroWindow } from "../components/ui/RetroWindow";
import { AskComposer } from "../features/ask/AskComposer";
import "./showcase.css";
import {
  Analysis,
  Answer,
  Collection,
  Lab,
  Tasks,
  request,
  type CollectionEmail,
} from "./api";

function useRequest<T>() {
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

function Failure({ code }: { code: string }) {
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
        {["What is the Atlas workshop date?", "ما تاريخ الورشة؟", "What meetings do I have this week?", "هل عندي مهام متأخرة؟", "What is the latest update on ORDER-778?"].map((q) => (
          <button key={q} onClick={() => setQuestion(q)}>
            {q}
          </button>
        ))}
      </div>
      <p className="text-sm">{t("استرجاع E5 متعلم، وإجابات استخراجيّة حتمية؛ ليست توليد LLM.", "Learned E5 retrieval with deterministic extractive answers, not LLM generation.")}</p>
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
      <Failure code={state.error} />
      {state.data && (
        <section aria-label={t("الإجابة", "Answer")}>
          <p className="whitespace-pre-wrap" dir="auto">
            {state.data.answer}
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
              <Link to={`/?email=${s.email_id}`}>
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

function Intelligence({ email }: { email: CollectionEmail }) {
  const { t } = useLocale();
  const state = useRequest<z.infer<typeof Analysis>>();
  const [subject, setSubject] = useState(email.subject);
  const [body, setBody] = useState(email.body);
  return (
    <RetroWindow
      title={t("تحليل البريد", "Email Intelligence")}
      bodyClassName="p-4 flex flex-col gap-3"
    >
      <p>
        {t(
          "تنبؤ فعلي من DistilBERT عبر ONNX. النموذج تجريبي ولم يجتز معيار الجودة.",
          "Live DistilBERT prediction via ONNX. The experimental model has not passed its quality gate.",
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
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={6000}
          rows={7}
          dir="auto"
        />
      </label>
      <small>
        {t(
          "استخدم نصاً خيالياً فقط. لا نحفظ المدخلات أو نستخدمها للتدريب.",
          "Use fictional text only. Inputs are not stored or used for training.",
        )}
      </small>
      <button
        className="primary"
        disabled={state.busy || !body.trim()}
        onClick={() => void state.run("analyze", Analysis, { subject, body })}
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
              <p>{t("المسؤول", "Responsible")}: {task.responsible ?? t("غير مذكور", "Not stated")}</p>
              <p>{t("حالة الموعد", "Deadline state")}: {task.deadline_state === "ambiguous" ? t("غير محسوم", "Ambiguous") : task.deadline_state === "explicit" ? t("مذكور", "Explicit") : t("غير مذكور", "Missing")}</p>
              {task.conditional && <p>{t("طلب مشروط؛ راجع الشرط في المصدر.", "Conditional request; check the source condition.")}</p>}
              {task.state === "superseded" && <p>{t("ألغته رسالة لاحقة.", "Cancelled by a later message.")} {task.superseded_by?.map(id => <Link key={id} to={`/?email=${id}`}>#{id} </Link>)}</p>}
              <Link to={`/?email=${task.email_id}`}>{t("افتح الرسالة الداعمة", "Open supporting email")}</Link>
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

function ModelLab() {
  const { t } = useLocale();
  const [data, setData] = useState<z.infer<typeof Lab>>();
  const [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    void request("lab", Lab, c.signal)
      .then(setData)
      .catch(() => {
        if (!c.signal.aborted) setError("request");
      });
    return () => c.abort();
  }, []);
  return (
    <RetroWindow
      title={t("مختبر النماذج", "Model Lab")}
      bodyClassName="p-4 flex flex-col gap-3"
    >
      <Failure code={error} />
      {data ? (
        <>
          <h2>{data.checkpoint}</h2>
          <p>{data.methodology}</p>
          <p>{data.inference}</p>
          <p>
            {t(
              "فشل معيار الجودة؛ لا توجد مجموعة اختبار نهائية مستقلة وممثلة.",
              "Quality gate FAILED: no independent representative final holdout.",
            )}
          </p>
          <p>
            {t(
              "تشخيص تطوير مستهلك وليس دقة عامة",
              "Consumed development diagnostics, not general accuracy",
            )}
            : n={data.development.n}, top-1=
            {(data.development.top1_accuracy * 100).toFixed(0)}%, macro-F1=
            {data.development.top1_macro_f1.toFixed(4)}
          </p>
          <ul>
            {Object.entries(data.languages).map(([name, scores]) => (
              <li key={name}>
                {name}: {scores.correct}/{scores.n} ·{" "}
                {t(
                  "عينة تطوير صغيرة، وتصنيف اللغة استدلالي",
                  "Small development slice; heuristic language labels",
                )}
              </li>
            ))}
          </ul>
          <p>
            {t("مصدر الأوزان", "Weight identity")}:{" "}
            <code className="break-all">{data.weight_sha256}</code>
          </p>
          <p>
            {t("الأدلة المسجلة", "Recorded evidence")}: {data.evidence_date}
          </p>
          <a
            href="https://github.com/tala-bulids/inbox-nizer/blob/codex/inbox-nizer-release/docs/release/V03_V10_EVIDENCE.md"
            target="_blank"
            rel="noreferrer"
          >
            {t(
              "المنهجية والتجارب والقيود",
              "Methodology, experiments and limitations",
            )}
          </a>
          <Link to="/intelligence">
            {t("جرّب التنبؤ الفعلي", "Try live prediction")}
          </Link>
        </>
      ) : (
        !error && (
          <p role="status">{t("جارٍ تحميل الأدلة…", "Loading evidence…")}</p>
        )
      )}
    </RetroWindow>
  );
}

function Workspace() {
  const { t, language, toggle } = useLocale();
  const [data, setData] = useState<z.infer<typeof Collection>>();
  const [error, setError] = useState("");
  const [params, setParams] = useSearchParams();
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
              ["/intelligence", "تحليل البريد", "Email Intelligence"],
              ["/lab", "مختبر النماذج", "Model Lab"],
            ] as const
          ).map(([path, ar, en]) => (
            <NavLink key={path} to={{ pathname: path, search: params.toString() }} end>
              {t(ar, en)}
            </NavLink>
          ))}
        </nav>
        {data?.metadata && <p className="text-sm">{t("تاريخ المجموعة المرجعي", "Collection reference date")}: {data.metadata.reference_datetime} · {t("الأسبوع يبدأ يوم الاثنين. هذه مجموعة خيالية وليست تقويمك الشخصي.", "Week starts Monday. This fictional collection is not your personal calendar.")}</p>}
        <Failure code={error} />
        {!data && !error && (
          <p role="status">
            {t("جارٍ تحميل المجموعة…", "Loading collection…")}
          </p>
        )}
        {selected && (
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-4">
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
                    "هذه المجموعة ليست بيانات تدريب أو اختبار جودة.",
                    "This collection is neither training data nor a quality benchmark.",
                  )}
                </small>
              </RetroWindow>
            </aside>
            <section className="min-w-0">
              <Routes>
                <Route index element={<Ask />} />
                <Route
                  path="tasks"
                  element={<SmartTasks key={selected.id} email={selected} />}
                />
                <Route
                  path="intelligence"
                  element={<Intelligence key={selected.id} email={selected} />}
                />
                <Route path="lab" element={<ModelLab />} />
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
