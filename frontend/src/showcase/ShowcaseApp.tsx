import { useEffect, useRef, useState, type ReactNode } from "react";
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
import { ModelLab } from "./ModelLab";
import {
  Prediction,
  Answer,
  Collection,
  Tasks,
  request,
  type CollectionEmail,
} from "./api";
import "./showcase.css";

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
    <p role="alert" className="notice">
      {code === "model"
        ? t(
            "تعذر تشغيل النموذج الآن. حاول مرة أخرى لاحقًا.",
            "The model is unavailable. Please try again later.",
          )
        : code === "busy"
          ? t(
              "النظام مشغول الآن. حاول بعد قليل.",
              "The model is busy. Please retry shortly.",
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

export function Panel({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="feature-panel">
      <header className="section-heading">
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </header>
      {children}
    </section>
  );
}

const categories: Record<string, string> = {
  Business: "أعمال",
  "Customer Support": "دعم العملاء",
  "Events & Invitations": "فعاليات ودعوات",
  "Finance & Bills": "شؤون مالية وفواتير",
  "Job Application": "طلبات توظيف",
  Newsletters: "نشرات بريدية",
  Personal: "رسائل شخصية",
  Promotions: "عروض ترويجية",
  Reminders: "تذكيرات",
  "Travel & Bookings": "سفر وحجوزات",
};
export function categoryName(name: string, language: string) {
  return language === "ar" ? categories[name] || name : name;
}

function Home() {
  const { t } = useLocale();
  return (
    <div className="home">
      <section className="home-intro">
        <p className="eyebrow">
          {t(
            "مشروع في معالجة اللغة الطبيعية",
            "A natural language processing project",
          )}
        </p>
        <h1 dir="ltr">Inbox-nizer</h1>
        <h2>
          {t(
            "فهم البريد الإلكتروني باستخدام الذكاء الاصطناعي",
            "Understanding email with AI",
          )}
        </h2>
        <p className="home-description">
          {t(
            "مشروع يهدف إلى الاستفادة من الذكاء الاصطناعي في فهم محتوى الرسائل الإلكترونية، وتصنيفها، والإجابة عن الأسئلة المتعلقة بها، واستخراج المهام المهمة منها.",
            "A project exploring how AI can understand email, classify messages, answer questions about their content, and extract tasks.",
          )}
        </p>
        <div className="actions">
          <Link className="button primary" to="/ask">
            {t("جرّب المشروع", "Try the project")}{" "}
            <span aria-hidden="true">↗</span>
          </Link>
          <Link className="button quiet" to="/lab">
            {t("مختبر النماذج", "Explore Model Lab")}
          </Link>
        </div>
        <p className="home-notice">
          {t(
            "هذا الموقع نسخة توضيحية لعرض فكرة المشروع وتجربة النماذج المستخدمة فيه، وليس خدمة لإدارة بريدك الشخصي.",
            "This showcase presents the project and its models. It is not a service for managing your personal email.",
          )}
        </p>
      </section>
      <section
        className="home-capabilities"
        aria-label={t("استكشف المشروع", "Explore the project")}
      >
        {(
          [
            [
              "/ask",
              "01",
              "اسأل البريد",
              "Ask Mail",
              "ابحث في معنى الرسائل واقرأ الإجابة مع مصدرها.",
              "Find relevant messages and read answers with their sources.",
            ],
            [
              "/tasks",
              "02",
              "المهام",
              "Smart Tasks",
              "استخرج الطلبات والمواعيد من نص الرسالة.",
              "Extract requests and deadlines from a message.",
            ],
            [
              "/lab",
              "03",
              "مختبر النماذج",
              "Model Lab",
              "تعرّف على التجارب والنتائج وجرّب تصنيف الرسائل.",
              "Explore the experiments and results, then try classification.",
            ],
          ] as const
        ).map(([path, number, ar, en, arBody, enBody]) => (
          <Link to={path} key={path}>
            <span className="step-number">{number}</span>
            <h3>{t(ar, en)}</h3>
            <p>{t(arBody, enBody)}</p>
            <span className="text-link">
              {t("استكشف", "Explore")} <span aria-hidden="true">↗</span>
            </span>
          </Link>
        ))}
      </section>
    </div>
  );
}

function Ask() {
  const { t } = useLocale();
  const state = useRequest<z.infer<typeof Answer>>();
  const [question, setQuestion] = useState("");
  const submit = () => {
    if (question.trim())
      void state.run("ask", Answer, { question, mode: "grounded" });
  };
  const answer = state.data;
  return (
    <Panel
      title={t("اسأل البريد", "Ask Mail")}
      description={t(
        "اطرح سؤالًا عن الرسائل الموجودة في المشروع، وسيبحث النظام عن المعلومات المتعلقة بسؤالك ويعرض الإجابة مع مصدرها.",
        "Ask about the project's messages. The system finds relevant information and shows an answer with its source.",
      )}
    >
      <form
        className="question-form"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <label htmlFor="question">{t("سؤالك", "Your question")}</label>
        <textarea
          id="question"
          dir="auto"
          rows={3}
          maxLength={1000}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("اكتب سؤالك هنا...", "Write your question here…")}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              (e.ctrlKey || e.metaKey) &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <div className="form-actions">
          <small>
            {t(
              "تُستخرج الإجابة من الرسائل، ويمكنك مراجعة مصدرها.",
              "Answers are extracted from messages, with sources you can check.",
            )}
          </small>
          <button className="primary" disabled={state.busy || !question.trim()}>
            {state.busy ? t("جارٍ البحث…", "Searching…") : t("اسأل", "Ask")}
          </button>
        </div>
      </form>
      <div
        className="suggestions"
        aria-label={t("أسئلة مقترحة", "Suggested questions")}
      >
        {[
          t("ما تاريخ الورشة؟", "What is the Atlas workshop date?"),
          t(
            "ما آخر تحديث للطلب ORDER-778؟",
            "What is the latest update on ORDER-778?",
          ),
        ].map((q) => (
          <button key={q} onClick={() => setQuestion(q)}>
            {q}
          </button>
        ))}
      </div>
      <Failure code={state.error} />
      {answer && (
        <section
          className="answer-result"
          aria-label={t("الإجابة", "Answer")}
          aria-live="polite"
        >
          <h2>{t("الإجابة", "Answer")}</h2>
          <p className="answer-copy" dir="auto">
            {answer.status !== "answered"
              ? t(
                  "لم أجد معلومات كافية في الرسائل للإجابة عن هذا السؤال.",
                  "I couldn't find enough information in the messages to answer this question.",
                )
              : answer.answer.split(/(\[email_id=\d+\])/g).map((part, i) => {
                  const id = /^\[email_id=(\d+)\]$/.exec(part)?.[1];
                  return id &&
                    answer.sources.some((s) => s.email_id === Number(id)) ? (
                    <Link
                      className="citation"
                      key={i}
                      to={`/collection?email=${id}`}
                      aria-label={`${t("المصدر", "Source")} ${id}`}
                    >
                      [
                      {answer.sources.findIndex(
                        (s) => s.email_id === Number(id),
                      ) + 1}
                      ]
                    </Link>
                  ) : (
                    part
                  );
                })}
          </p>
          {answer.verification === "not_semantically_verified" && (
            <p className="notice">
              {t(
                "راجع الرسائل المرتبطة للتأكد من معنى الإجابة.",
                "Check the linked messages to verify the answer's meaning.",
              )}
            </p>
          )}
          {answer.sources.length > 0 && (
            <section
              className="answer-sources"
              aria-label={t("الرسائل المرتبطة بالإجابة", "Supporting messages")}
            >
              <h3>{t("الرسائل المرتبطة بالإجابة", "Supporting messages")}</h3>
              {answer.sources.map((s, i) => (
                <details key={s.email_id}>
                  <summary>
                    <span className="source-number">{i + 1}</span>
                    <span dir="auto">{s.subject}</span>
                  </summary>
                  <blockquote dir="auto">{s.content}</blockquote>
                  <Link to={`/collection?email=${s.email_id}`}>
                    {t("افتح الرسالة الأصلية", "Open source message")}
                  </Link>
                </details>
              ))}
            </section>
          )}
        </section>
      )}
    </Panel>
  );
}

export function Intelligence({ email }: { email: CollectionEmail }) {
  const { t, language } = useLocale();
  const state = useRequest<z.infer<typeof Prediction>>();
  const [subject, setSubject] = useState(email.subject);
  const [body, setBody] = useState(email.body);
  return (
    <section className="playground">
      <h2>{t("جرّب تصنيف رسالة", "Try classifying a message")}</h2>
      <p>
        {t(
          "يستخدم التصنيف TF-IDF مع الانحدار اللوجستي. جُرّب النموذج على بيانات إنجليزية؛ لم يُقيّم تصنيفه للعربية.",
          "Classification uses TF-IDF with logistic regression. The model was evaluated on English data; Arabic classification has not been evaluated.",
        )}
      </p>
      <label>
        {t("عنوان الرسالة", "Subject")}
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          maxLength={300}
          dir="auto"
        />
      </label>
      <label>
        {t("محتوى الرسالة", "Text")}
        <textarea
          aria-label={t("محتوى الرسالة", "Text")}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={6000}
          rows={6}
          dir="auto"
        />
      </label>
      <div className="form-actions">
        <small>
          {t(
            "استخدم نصًا افتراضيًا. لا تُحفظ المدخلات أو تُستخدم للتدريب.",
            "Use fictional text. Inputs are not stored or used for training.",
          )}
        </small>
        <button
          className="primary"
          disabled={state.busy || !body.trim()}
          onClick={() =>
            void state.run("predict", Prediction, { subject, body })
          }
        >
          {state.busy
            ? t("جارٍ التحليل…", "Analyzing…")
            : t("صنّف الرسالة", "Run prediction")}
        </button>
      </div>
      <Failure code={state.error} />
      {state.data && (
        <section
          className="prediction-result"
          aria-label={t("نتيجة التصنيف", "Analysis result")}
          aria-live="polite"
        >
          {state.data.predictions.map((p) => (
            <div key={p.category}>
              <span className="eyebrow">{t("التصنيف", "Classification")}</span>
              <h3>{categoryName(p.category, language)}</h3>
              <p>
                {t("درجة النموذج", "Model score")}:{" "}
                <bdi>{p.confidence.toFixed(3)}</bdi>
              </p>
            </div>
          ))}
          <small>
            {t(
              "الدرجة ليست احتمالًا مؤكدًا لصحة التصنيف.",
              "The raw model score is not a probability of correctness.",
            )}
          </small>
          <p className="muted">
            {t("زمن المعالجة", "Processing time")}:{" "}
            <bdi>{state.data.processing_ms.toFixed(1)} ms</bdi>
            {state.data.cold_load_included &&
              t(" (يشمل تحميل النموذج)", " (includes model loading)")}
          </p>
          <h3>{t("مقتطف من الرسالة", "Extractive summary")}</h3>
          <blockquote dir="auto">{state.data.summary}</blockquote>
        </section>
      )}
    </section>
  );
}

function SmartTasks({
  email,
  selector,
}: {
  email: CollectionEmail;
  selector: ReactNode;
}) {
  const { t } = useLocale();
  const state = useRequest<z.infer<typeof Tasks>>();
  return (
    <Panel
      title={t("المهام", "Smart Tasks")}
      description={t(
        "يعرض هذا القسم المهام التي استخرجها النظام من محتوى الرسائل، مثل المواعيد والطلبات والأعمال المطلوب إنجازها.",
        "Find tasks in the messages, including requests, deadlines, and work to follow up on.",
      )}
    >
      <div className="task-selector">{selector}</div>
      <div className="actions">
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
          className="quiet"
          disabled={state.busy}
          onClick={() => void state.run("tasks", Tasks)}
        >
          {t("مهام جميع الرسائل", "Explore all tasks")}
        </button>
      </div>
      <Failure code={state.error} />
      {state.data && (
        <div className="task-list" aria-live="polite">
          {state.data.tasks.length ? (
            state.data.tasks.map((task, i) => (
              <article className="task-item" key={i}>
                <h2 dir="auto">{task.task}</h2>
                <dl className="task-meta">
                  <div>
                    <dt>{t("الموعد", "Deadline")}</dt>
                    <dd>
                      {task.deadline_date || task.deadline_text ? (
                        <bdi>{task.deadline_date ?? task.deadline_text}</bdi>
                      ) : (
                        t("غير مذكور في الرسالة", "Not stated in the message")
                      )}
                    </dd>
                  </div>
                  {task.responsible && (
                    <div>
                      <dt>{t("المسؤول", "Responsible")}</dt>
                      <dd dir="auto">{task.responsible}</dd>
                    </div>
                  )}
                </dl>
                {task.deadline_state === "ambiguous" && (
                  <p>
                    {t(
                      "الموعد غير واضح؛ راجع الرسالة الأصلية.",
                      "The deadline is unclear; check the original message.",
                    )}
                  </p>
                )}
                {task.conditional && (
                  <p>
                    {t(
                      "هذا الطلب مرتبط بشرط مذكور في الرسالة.",
                      "This request depends on a condition in the message.",
                    )}
                  </p>
                )}
                {task.state === "superseded" && (
                  <p>
                    {t(
                      "أُلغيت هذه المهمة في رسالة لاحقة.",
                      "This task was cancelled in a later message.",
                    )}{" "}
                    {task.superseded_by?.map((id) => (
                      <Link key={id} to={`/collection?email=${id}`}>
                        {t("راجع التحديث", "View update")}
                      </Link>
                    ))}
                  </p>
                )}
                <details>
                  <summary>{t("الرسالة الأصلية", "Original source")}</summary>
                  <blockquote dir="auto">
                    {task.evidence.text ?? task.evidence.body}
                  </blockquote>
                  <Link to={`/collection?email=${task.email_id}`}>
                    {t("افتح الرسالة", "Open supporting email")}
                  </Link>
                </details>
              </article>
            ))
          ) : (
            <p>
              {t(
                "لم أجد مهمة واضحة في هذه الرسالة.",
                "No clear task was found in this message.",
              )}
            </p>
          )}
        </div>
      )}
    </Panel>
  );
}

function EmailReader({
  email,
  emails,
  select,
  hideSelector = false,
}: {
  email: CollectionEmail;
  emails: CollectionEmail[];
  select: (id: string) => void;
  hideSelector?: boolean;
}) {
  const { t } = useLocale();
  return (
    <aside
      className="email-reader"
      aria-label={t("الرسالة المختارة", "Selected message")}
    >
      {!hideSelector && (
        <label>
          {t("اختر رسالة", "Choose a source")}
          <select value={email.id} onChange={(e) => select(e.target.value)}>
            {emails.map((e) => (
              <option key={e.id} value={e.id}>
                {e.subject}
              </option>
            ))}
          </select>
        </label>
      )}
      <article>
        <h2 dir="auto">{email.subject}</h2>
        <dl className="email-meta">
          <div>
            <dt>{t("المرسل", "Sender")}</dt>
            <dd>
              <bdi>{email.sender}</bdi>
            </dd>
          </div>
          <div>
            <dt>{t("التاريخ", "Date")}</dt>
            <dd>
              <bdi>{email.date.slice(0, 10)}</bdi>
            </dd>
          </div>
        </dl>
        <p className="email-body" dir="auto">
          {email.body}
        </p>
      </article>
    </aside>
  );
}

function Workspace() {
  const { t, language, toggle } = useLocale();
  const [data, setData] = useState<z.infer<typeof Collection>>();
  const [error, setError] = useState("");
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const [filter, setFilter] = useState("");
  const isHome = location.pathname === "/";
  const isLab = ["/lab", "/intelligence"].includes(location.pathname);
  const isCollection = location.pathname === "/collection";
  const mainRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const c = new AbortController();
    void request("collection", Collection, c.signal)
      .then(setData)
      .catch(() => {
        if (!c.signal.aborted) setError("request");
      });
    return () => c.abort();
  }, []);
  useEffect(() => {
    window.scrollTo?.(0, 0);
    mainRef.current?.focus({ preventScroll: true });
  }, [location.pathname]);
  useEffect(() => {
    document.title = t(
      "Inbox-nizer | مشروع لفهم البريد",
      "Inbox-nizer | Email AI project",
    );
  }, [t]);
  const selected =
    data?.emails.find((e) => e.id === Number(params.get("email"))) ??
    data?.emails[0];
  const matches =
    data?.emails.filter((e) =>
      `${e.subject} ${e.body} ${e.sender}`
        .toLowerCase()
        .includes(filter.toLowerCase()),
    ) ?? [];
  return (
    <div className="showcase">
      <a className="skip-link" href="#main">
        {t("انتقل إلى المحتوى", "Skip to content")}
      </a>
      <header className="site-header">
        <div className="header-inner">
          <Link className="brand" to="/" dir="ltr">
            <span className="brand-mark" aria-hidden="true">
              ✉
            </span>{" "}
            Inbox-nizer
          </Link>
          <button
            className="language-toggle"
            onClick={toggle}
            aria-label={
              language === "ar" ? "Switch to English" : "التبديل للعربية"
            }
          >
            <span lang={language === "ar" ? "en" : "ar"}>
              {language === "ar" ? "English" : "العربية"}
            </span>
          </button>
        </div>
      </header>
      <div className="page-shell">
        <nav
          className="showcase-nav"
          aria-label={t("أقسام المشروع", "Project sections")}
        >
          {(
            [
              ["/", "الرئيسية", "Home"],
              ["/ask", "اسأل البريد", "Ask Mail"],
              ["/tasks", "المهام", "Smart Tasks"],
              ["/collection", "الرسائل", "Email Collection"],
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
        <main id="main" tabIndex={-1} ref={mainRef}>
          {isHome ? (
            <Home />
          ) : (
            <>
              <Failure code={error} />
              {!data && !error && (
                <p role="status">
                  {t("جارٍ تحميل الرسائل…", "Loading messages…")}
                </p>
              )}
              {selected && (
                <div
                  className={
                    isLab
                      ? "lab-page"
                      : `workspace-grid ${isCollection ? "collection-grid" : ""}`
                  }
                >
                  {!isLab && (
                    <EmailReader
                      email={selected}
                      emails={data!.emails}
                      select={(id) => setParams({ email: id })}
                      hideSelector={location.pathname === "/tasks"}
                    />
                  )}
                  <div className="workspace-content">
                    <Routes>
                      <Route path="ask" element={<Ask />} />
                      <Route
                        path="tasks"
                        element={
                          <SmartTasks
                            key={selected.id}
                            email={selected}
                            selector={
                              <label>
                                {t("اختر رسالة", "Choose a source")}
                                <select
                                  value={selected.id}
                                  onChange={(e) =>
                                    setParams({ email: e.target.value })
                                  }
                                >
                                  {data!.emails.map((e) => (
                                    <option key={e.id} value={e.id}>
                                      {e.subject}
                                    </option>
                                  ))}
                                </select>
                              </label>
                            }
                          />
                        }
                      />
                      <Route
                        path="intelligence"
                        element={<ModelLab email={selected} />}
                      />
                      <Route
                        path="lab"
                        element={<ModelLab email={selected} />}
                      />
                      <Route
                        path="collection"
                        element={
                          <Panel
                            title={t("الرسائل", "Email Collection")}
                            description={t(
                              "مجموعة من الرسائل الافتراضية أُعدت لتجربة خصائص المشروع وعرض طريقة عمل النماذج.",
                              "Fictional messages created to explore the project's features and show how the models work.",
                            )}
                          >
                            <label>
                              {t("ابحث في الرسائل", "Filter collection")}
                              <input
                                value={filter}
                                onChange={(e) => setFilter(e.target.value)}
                                dir="auto"
                                maxLength={200}
                              />
                            </label>
                            <h2 className="list-heading">
                              {t("جميع الرسائل", "All messages")}{" "}
                              <span>({matches.length})</span>
                            </h2>
                            <ul className="collection-list">
                              {matches.map((e) => (
                                <li key={e.id}>
                                  <Link
                                    aria-current={
                                      e.id === selected.id ? "true" : undefined
                                    }
                                    to={`/collection?email=${e.id}`}
                                  >
                                    <strong dir="auto">{e.subject}</strong>
                                    <small>
                                      <bdi>{e.sender}</bdi>
                                      <bdi>{e.date.slice(0, 10)}</bdi>
                                    </small>
                                  </Link>
                                </li>
                              ))}
                            </ul>
                            {!matches.length && (
                              <p role="status">
                                {t(
                                  "لا توجد رسائل تطابق البحث.",
                                  "No matching messages",
                                )}
                              </p>
                            )}
                          </Panel>
                        }
                      />
                      <Route
                        path="*"
                        element={
                          <Link to="/">
                            {t("العودة للرئيسية", "Return home")}
                          </Link>
                        }
                      />
                    </Routes>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
        <footer className="site-footer">
          <span>
            {t(
              "Inbox-nizer · مشروع في الذكاء الاصطناعي",
              "Inbox-nizer · An AI project",
            )}
          </span>
          <a
            href="https://github.com/tala-bulids/inbox-nizer"
            target="_blank"
            rel="noreferrer"
          >
            {t("المشروع على GitHub", "View on GitHub")}{" "}
            <span aria-hidden="true">↗</span>
          </a>
        </footer>
      </div>
    </div>
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
