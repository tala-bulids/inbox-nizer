import { useEffect, useState } from "react";
import { z } from "zod";
import { Link } from "react-router-dom";
import { useLocale } from "../app/locale";
import { Portfolio, request, type CollectionEmail } from "./api";
import { Failure, Intelligence, categoryName } from "./ShowcaseApp";

const names: Record<string, string> = {
  A: "TF-IDF + Logistic Regression",
  B: "DistilBERT",
  C: "Multilingual E5 + Logistic Regression",
};
const pct = (n: number) => `${(n * 100).toFixed(1)}%`;
const repo =
  "https://github.com/tala-bulids/inbox-nizer/blob/c2ef87094bc01860b6e763f02dafe799d88dca13/";
export function ModelLab({ email }: { email: CollectionEmail }) {
  const { t, language } = useLocale();
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
    <section className="model-lab">
      <header className="section-heading">
        <p className="eyebrow">
          {t("من الفكرة إلى تشغيل النماذج", "From idea to working models")}
        </p>
        <h1>{t("مختبر النماذج", "Model Lab")}</h1>
        <p>
          {t(
            "في هذا القسم أعرض خطوات العمل على نماذج الذكاء الاصطناعي، والتجارب التي أجريتها، والنتائج التي توصلت إليها.",
            "Here I explain the AI work behind the project: the models I explored, the experiments I ran, and what I learned from the results.",
          )}
        </p>
      </header>
      <div
        className="lab-tabs"
        role="group"
        aria-label={t("أقسام المختبر", "Lab sections")}
      >
        {(
          [
            ["overview", "فكرة العمل", "Overview"],
            ["training", "البيانات والتدريب", "Training & data"],
            ["evaluation", "نتائج التجارب", "Evaluation"],
            ["playground", "جرّب التصنيف", "Playground"],
          ] as const
        ).map(([id, ar, en]) => (
          <button
            key={id}
            aria-pressed={section === id}
            aria-controls="lab-content"
            onClick={() => setSection(id)}
          >
            {t(ar, en)}
          </button>
        ))}
      </div>
      <Failure code={error} />
      {!data && !error && (
        <p role="status">{t("جارٍ تحميل النتائج…", "Loading results…")}</p>
      )}
      {data && model && (
        <div id="lab-content" className="lab-content">
          {section === "overview" && (
            <>
              <section className="lab-section">
                <h2>{t("فكرة العمل", "The idea")}</h2>
                <p>
                  {t(
                    "بدأت العمل على فكرة استخدام الذكاء الاصطناعي لفهم الرسائل الإلكترونية بدلًا من الاكتفاء بعرضها وترتيبها. ركزت على تصنيف الرسائل، والبحث في محتواها، واستخراج المهام منها.",
                    "I started with the idea of using AI to understand email content. I focused on classification, finding information within messages, and extracting tasks.",
                  )}
                </p>
                <figure className="architecture">
                  <figcaption>
                    {t("كيف يعمل المشروع؟", "How does the project work?")}
                  </figcaption>
                  <div className="flow-entry">
                    <span>{t("الرسائل الإلكترونية", "Email messages")}</span>
                    <span aria-hidden="true">↓</span>
                    <span>
                      {t(
                        "معالجة النصوص حسب المهمة",
                        "Text preparation for each task",
                      )}
                    </span>
                  </div>
                  <p className="flow-split">
                    {t("ثلاثة مسارات مستقلة", "Three separate paths")}
                  </p>
                  <div className="flow-branches">
                    <div>
                      <span className="flow-arrow" aria-hidden="true">
                        ↓
                      </span>
                      <h3>{t("تصنيف الرسائل", "Classification")}</h3>
                      <p dir="ltr">TF-IDF → Logistic Regression</p>
                      <span aria-hidden="true">↓</span>
                      <p>
                        {t(
                          "تصنيف الرسالة ودرجة النموذج",
                          "Category and model score",
                        )}
                      </p>
                    </div>
                    <div>
                      <span className="flow-arrow" aria-hidden="true">
                        ↓
                      </span>
                      <h3>{t("البحث والإجابة", "Search & answers")}</h3>
                      <p>
                        {t(
                          "تمثيل السؤال بـ E5 ← البحث في تمثيلات الرسائل",
                          "E5 query embedding → search message embeddings",
                        )}
                      </p>
                      <span aria-hidden="true">↓</span>
                      <p>
                        {t(
                          "إجابة مستخرجة من النص مع مصادرها",
                          "Extractive answer with sources",
                        )}
                      </p>
                    </div>
                    <div>
                      <span className="flow-arrow" aria-hidden="true">
                        ↓
                      </span>
                      <h3>{t("استخراج المهام", "Task extraction")}</h3>
                      <p>
                        {t(
                          "قواعد نصية للطلبات والمواعيد",
                          "Text rules for requests and deadlines",
                        )}
                      </p>
                      <span aria-hidden="true">↓</span>
                      <p>
                        {t(
                          "مهمة وموعد مرتبطان بالرسالة",
                          "Task and deadline linked to a message",
                        )}
                      </p>
                    </div>
                  </div>
                </figure>
                <p className="muted">
                  {t(
                    "استخراج المهام يعتمد على قواعد عربية وإنجليزية، وليس على نموذج منفصل درّبته.",
                    "Task extraction uses Arabic and English rules, not a separately trained model.",
                  )}
                </p>
              </section>
              <section className="lab-section">
                <h2>{t("البحث الدلالي", "Semantic search")}</h2>
                <p>
                  {t(
                    "استخدمت البحث الدلالي للوصول إلى الرسائل المرتبطة بمعنى السؤال، بدلًا من الاعتماد على تطابق الكلمات فقط.",
                    "I used semantic search to find messages related to the meaning of a question, rather than relying only on matching words.",
                  )}
                </p>
                <p>
                  {t(
                    "التمثيلات العددية (Embeddings) تحوّل النص إلى أرقام تلخّص معناه. يقارن النظام تمثيل السؤال بتمثيلات مقاطع الرسائل، ثم يختار المعلومات التي يمكن إسنادها إلى النص ويعرض مصادرها. إذا لم يجد دليلًا كافيًا، يوضح ذلك بدلًا من اختراع إجابة.",
                    "Embeddings represent text as numbers that capture meaning. The system compares the question with message passages, selects information supported by the text, and links the sources. If the evidence is insufficient, it says so instead of inventing an answer.",
                  )}
                </p>
                <p className="muted">
                  {t(
                    "الإجابات هنا استخراجية؛ لا يستخدم هذا المسار نموذج لغة لتوليد محادثة.",
                    "Answers are extractive; this pipeline does not use a generative chatbot.",
                  )}
                </p>
              </section>
              <section className="lab-section">
                <h2>
                  {t(
                    "النموذج المستخدم في الموقع",
                    "The models running on this site",
                  )}
                </h2>
                <dl className="method-list">
                  <div>
                    <dt>{t("التصنيف", "Classification")}</dt>
                    <dd>
                      <strong dir="ltr">TF-IDF + Logistic Regression</strong>
                      <p>
                        {t(
                          "درّبت تمثيل TF-IDF والمصنّف الخطي على جزء التدريب. اخترت هذا النموذج لأنه حقق نتائج تحقق أفضل من تجربة E5 مع مصنّف خطي، بزمن استدلال واستهلاك ذاكرة أقل.",
                          "I fitted TF-IDF features and the linear classifier on the training split. I selected it over E5 with a linear classifier for its stronger validation results, lower inference latency, and lower memory use.",
                        )}
                      </p>
                    </dd>
                  </div>
                  <div>
                    <dt>{t("البحث", "Retrieval")}</dt>
                    <dd>
                      <strong dir="ltr">Multilingual E5 small</strong>
                      <p>
                        {t(
                          "أعدت استخدام نموذج جاهز متعدد اللغات دون إعادة تدريبه. يستخدم الموقع نسخة ONNX INT8 لتمثيل السؤال، ويبحث في تمثيلات الرسائل المحسوبة مسبقًا بالنموذج الأصلي FP32.",
                          "I reused a pretrained multilingual model without retraining it. The site encodes questions with ONNX INT8 and searches message embeddings precomputed with the original FP32 model.",
                        )}
                      </p>
                    </dd>
                  </div>
                </dl>
                <p>
                  {t(
                    "اختيار النماذج راعى نتائج التقييم والموارد المتاحة معًا. نجاح تشغيل الموقع على الاستضافة لا يعني اعتماد جودة النماذج للاستخدام الفعلي.",
                    "Model selection considered both evaluation results and practical resource requirements. Successful hosting does not establish production model quality.",
                  )}
                </p>
                <Link className="text-link" to="/ask">
                  {t("جرّب البحث في الرسائل", "Try searching the messages")} ↗
                </Link>
              </section>
              <section className="lab-section">
                <h2>{t("تحسين الأداء", "Memory optimization")}</h2>
                <p>
                  {t(
                    "عملت أيضًا على تحسين استهلاك الذاكرة حتى يتمكن الموقع من تشغيل النماذج على استضافة مجانية دون تغيير أوزان النماذج أو حدود الإدخال أثناء تحسين الذاكرة النهائي.",
                    "I also optimized memory use so the models could run on free hosting. The final memory optimization changed neither model weights nor input limits.",
                  )}
                </p>
                <div
                  className="memory-comparison"
                  aria-label={t(
                    "مقارنة ذروة الذاكرة في Linux",
                    "Linux peak memory comparison",
                  )}
                >
                  <div>
                    <span>{t("قبل التحسين", "Before")}</span>
                    <strong dir="ltr">
                      500.01 <small>MiB</small>
                    </strong>
                    <div className="memory-track">
                      <span style={{ width: "97.66%" }} />
                    </div>
                  </div>
                  <div>
                    <span>{t("بعد التحسين", "After")}</span>
                    <strong dir="ltr">
                      333.14 <small>MiB</small>
                    </strong>
                    <div className="memory-track">
                      <span style={{ width: "65.07%" }} />
                    </div>
                  </div>
                </div>
                <p>
                  <strong>
                    {t(
                      "انخفاض بنسبة 33.37% في ذروة الذاكرة.",
                      "33.37% lower peak memory.",
                    )}
                  </strong>{" "}
                  {t(
                    "القياس من اختبار Linux مقيّد بذاكرة 512 MiB، وحصة CPU قدرها 0.1، ومن دون swap. الهدف الهندسي كان 400 MiB.",
                    "Measured in constrained Linux with 512 MiB memory, 0.1 CPU, and no swap. The engineering target was 400 MiB.",
                  )}
                </p>
                <p>
                  {t(
                    "عدّلت سياسة تخصيص الذاكرة لإرجاع المساحات المؤقتة الكبيرة للنظام. ارتفع زمن تمثيل الإدخال الأقصى، 512 رمزًا، من 3.90 إلى 6.60 ثانية. هذه مقارنة للاختبار نفسه، وليست زمن الاستجابة لكل سؤال أو قياسًا دوريًا من Render.",
                    "I adjusted memory allocation so large temporary buffers could be returned to the OS. Encoding the maximum 512-token input increased from 3.90 to 6.60 seconds. These are measurements from the same qualification workload, not every question's latency or sampled Render usage.",
                  )}
                </p>
                <p className="muted">
                  {t(
                    "نجحت اختبارات التشغيل على خدمة Render Free الأصلية. أرقام الذاكرة أعلاه تخص اختبار Linux فقط.",
                    "Live acceptance passed on the original Render Free service. The memory figures above refer only to Linux qualification.",
                  )}
                </p>
              </section>
            </>
          )}
          {section === "training" && (
            <>
              <section className="lab-section">
                <h2>{t("البيانات", "Data")}</h2>
                <p>
                  {t(
                    "استخدمت مجموعة بيانات لتدريب نموذج تصنيف الرسائل وتقييمه، بالإضافة إلى رسائل افتراضية باللغتين العربية والإنجليزية لتجربة خصائص المشروع.",
                    "I used a dataset to train and evaluate email classification, alongside fictional Arabic and English messages for the interactive showcase.",
                  )}
                </p>
                <p>
                  <a
                    href={`https://huggingface.co/datasets/${data.dataset.source.repository}/tree/${data.dataset.source.revision}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <bdi>{data.dataset.source.repository}</bdi> ↗
                  </a>
                </p>
                <p>
                  {t(
                    "مجموعة تصنيف إنجليزية تتضمن",
                    "The English classification dataset contains",
                  )}{" "}
                  <bdi>{data.dataset.usable_rows.toLocaleString("en")}</bdi>{" "}
                  {t(
                    "رسالة قابلة للاستخدام بعد التنظيف، موزعة على عشر فئات. يذكر الناشر ترخيص MIT ويتيح كود توليد اصطناعي؛ لم أتحقق من منشأ كل رسالة على حدة.",
                    "usable messages after cleaning, across ten categories. The publisher declares an MIT license and provides synthetic generation code; individual message provenance is unverified.",
                  )}
                </p>
                <div className="split-row">
                  {Object.entries(data.dataset.splits).map(([name, split]) => (
                    <div key={name}>
                      <strong>{split.rows.toLocaleString("en")}</strong>
                      <span>
                        {name === "train"
                          ? t("تدريب", "Training")
                          : name === "validation"
                            ? t("تحقق", "Validation")
                            : t(
                                "اختبار محجوز · لم يُقيّم",
                                "Reserved test · not evaluated",
                              )}
                      </span>
                    </div>
                  ))}
                </div>
                <p>
                  {t(
                    "جمعت النصوص المتشابهة قبل التقسيم لتقليل تسرّب البيانات، وعزلت الوسوم المتناقضة. لكن غياب معلومات المرسل والمحادثة، واستخدام البيانات في تجارب سابقة، يمنع اعتبار الاختبار المحجوز تقييمًا نهائيًا مستقلًا.",
                    "I grouped similar texts before splitting to reduce leakage and quarantined contradictory labels. Missing sender/thread metadata and earlier use of the corpus mean the reserved test cannot serve as an independent final evaluation.",
                  )}
                </p>
                <p className="note">
                  {t(
                    "رسائل الموقع الـ24 أمثلة افتراضية منفصلة، وليست رسائل Gmail شخصية أو بيانات تدريب المصنّف.",
                    "The site's 24 fictional messages are separate demonstration examples, not personal Gmail data or classifier training data.",
                  )}
                </p>
              </section>
              <section className="lab-section">
                <h2>{t("تدريب النماذج", "Training experiments")}</h2>
                <p>
                  {t(
                    "جرّبت أكثر من طريقة لتصنيف الرسائل الإلكترونية، وقارنت أداءها لاختيار النموذج الأنسب للمشروع.",
                    "I explored several approaches to email classification and compared their results to choose a model for this project.",
                  )}
                </p>
                <article className="experiment">
                  <h3 dir="ltr">TF-IDF + Logistic Regression</h3>
                  <p>
                    {t(
                      "يحوّل TF-IDF الكلمات ومقاطع الحروف إلى سمات رقمية، مع وزن أكبر للمصطلحات المميزة. درّبت هذه السمات وعشرة مصنّفات انحدار لوجستي مستقلة على بيانات التدريب فقط. كان هذا خط الأساس البسيط والسريع، وهو المصنّف المستخدم الآن.",
                      "TF-IDF converts words and character sequences into weighted features, emphasizing distinctive terms. I fitted these features and ten independent logistic regression classifiers on training data only. This simple, fast baseline is the classifier now in use.",
                    )}
                  </p>
                </article>
                <article className="experiment">
                  <h3 dir="ltr">
                    DistilBERT · {t("تجارب سابقة", "historical experiments")}
                  </h3>
                  <p>
                    {t(
                      "DistilBERT نموذج لغوي مدرّب مسبقًا. في الضبط الدقيق (Fine-tuning)، تُعدّل بعض أوزانه لتناسب تصنيف الرسائل. يوثّق تقرير تجربة سابقة تدريب آخر طبقتين لثلاث دورات. أما نقطة الحفظ المستخدمة في المقارنة اللاحقة فجرى تقييمها فقط، ولا يتوفر تقسيم تدريبها الأصلي؛ لذلك استبعدتها من اختيار النموذج.",
                      "DistilBERT is a pretrained language model. Fine-tuning adapts some of its weights to email classification. A historical experiment report records training the last two layers for three epochs. The checkpoint used in the later comparison was evaluated only; its original training split is unavailable, so I excluded it from model selection.",
                    )}
                  </p>
                  <p className="muted">
                    {t(
                      "هاتان تجربتان تاريخيتان مختلفتان. لم أدرّب نموذج DistilBERT من الصفر، ولم أنفذ ضبطًا دقيقًا جديدًا في المقارنة الحالية.",
                      "These are different historical experiments. I did not train DistilBERT from scratch or run new transformer fine-tuning in the current comparison.",
                    )}
                  </p>
                </article>
                <article className="experiment">
                  <h3 dir="ltr">Multilingual E5 + Logistic Regression</h3>
                  <p>
                    {t(
                      "استخدمت E5 الجاهز لتحويل الرسالة إلى تمثيل عددي للجملة (Sentence Embedding)، وثبّتُّ أوزانه. درّبت المصنّف الخطي فوق هذه التمثيلات فقط، لاختبار فائدة السمات الدلالية. لم يتفوق على TF-IDF في هذه البيانات الإنجليزية، وقدرته متعددة اللغات لا تثبت جودة تصنيف البريد بالعربية.",
                      "I used pretrained E5 to produce sentence embeddings while keeping its weights frozen. I trained only the linear classifier on top, to test semantic features. It did not outperform TF-IDF on this English dataset, and multilingual pretraining does not prove Arabic email classification quality.",
                    )}
                  </p>
                </article>
              </section>
              <details className="research-details">
                <summary>
                  {t(
                    "تفاصيل التدريب وإعادة التجربة",
                    "Training details & reproducibility",
                  )}
                </summary>
                <p>
                  {t(
                    "تطبيع النصوص وتنظيف HTML وحجب بيانات الاتصال والروابط والأرقام الطويلة؛ تدريب المفردات على جزء التدريب فقط. بُذرة التقسيم:",
                    "Text normalization, HTML cleaning, and contact/URL/long-number redaction; vocabulary fitted on training only. Split seed:",
                  )}{" "}
                  <bdi>{data.dataset.seed}</bdi>.
                </p>
                <dl className="settings-list">
                  {Object.entries({
                    ...data.configuration.linear,
                    ...data.configuration.tfidf,
                  }).map(([key, value]) => (
                    <div key={key}>
                      <dt dir="ltr">{key}</dt>
                      <dd dir="ltr">{String(value)}</dd>
                    </div>
                  ))}
                </dl>
                <p>
                  {t(
                    "لم تُحفظ منحنيات خسارة عبر دورات التدريب. القيم التالية هي الخسارة النهائية للتدريب والتحقق، وليست منحنيات مُعاد بناؤها.",
                    "No epoch-by-epoch loss curves were saved. These are final training and validation losses, not reconstructed curves.",
                  )}
                </p>
                <div
                  className="lab-table"
                  role="region"
                  aria-label={t("خسارة التدريب", "Training loss")}
                  tabIndex={0}
                >
                  <table>
                    <caption>
                      {t(
                        "الخسارة اللوغاريتمية الثنائية غير الموزونة",
                        "Unweighted binary log loss",
                      )}
                    </caption>
                    <thead>
                      <tr>
                        <th>{t("النموذج", "Model")}</th>
                        <th>{t("التدريب", "Training")}</th>
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
                <a
                  href="/api/showcase/reproduction"
                  target="_blank"
                  rel="noreferrer"
                >
                  {t(
                    "المنهجية وأوامر إعادة التجربة",
                    "Methodology & reproduction commands",
                  )}{" "}
                  ↗
                </a>
                <p className="muted">
                  {t(
                    "هذا الرابط يعرض التوثيق فقط، ولا يشغّل تدريبًا.",
                    "This link displays documentation; it does not run training.",
                  )}
                </p>
              </details>
            </>
          )}
          {section === "evaluation" && (
            <>
              <section className="lab-section">
                <h2>{t("نتائج التجارب", "Experiment results")}</h2>
                <p>
                  {t(
                    "قارنت نتائج النماذج باستخدام مقاييس التقييم لاختيار الطريقة المناسبة للمشروع.",
                    "I compared evaluation metrics to choose an approach for the project.",
                  )}
                </p>
                <p>
                  {t(
                    "المقارنة الأساسية على 215 رسالة تحقق إنجليزية. استُخدمت هذه المجموعة لاختيار النموذج، لذلك الأرقام ليست نتائج اختبار نهائي مستقل.",
                    "The main comparison uses 215 English validation messages. This set informed model selection, so these are not independent final-test results.",
                  )}
                </p>
                <div
                  className="lab-table"
                  role="region"
                  aria-label={t(
                    "مقارنة نماذج التصنيف",
                    "Classifier comparison",
                  )}
                  tabIndex={0}
                >
                  <table>
                    <caption>
                      {t(
                        "النماذج المؤهلة للاختيار · المجموعة نفسها",
                        "Eligible candidates · same validation set",
                      )}
                    </caption>
                    <thead>
                      <tr>
                        <th>{t("النموذج", "Model")}</th>
                        <th>Accuracy</th>
                        <th>Macro F1</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.models
                        .filter((m) => m.id !== "B")
                        .map((m) => (
                          <tr key={m.id}>
                            <th>
                              {names[m.id]}
                              {m.id === data.selected && (
                                <small>
                                  {t("المستخدم في الموقع", "Used on this site")}
                                </small>
                              )}
                            </th>
                            <td>{pct(m.metrics.top1_accuracy)}</td>
                            <td>{m.metrics.top1_macro_f1.toFixed(3)}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
                <dl className="metric-definitions">
                  <div>
                    <dt>Accuracy</dt>
                    <dd>
                      {t(
                        "نسبة الرسائل التي طابق فيها التصنيف أحد الوسوم الصحيحة.",
                        "Share of messages whose predicted category matches any reference label.",
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Macro F1</dt>
                    <dd>
                      {t(
                        "متوسط التوازن بين الدقة والاسترجاع عبر الفئات بالتساوي. هنا يُقارن تصنيف واحد بكل الوسوم المرجعية للرسالة.",
                        "The balance of precision and recall, averaged equally across categories. Here, one prediction is compared with all of a message's reference labels.",
                      )}
                    </dd>
                  </div>
                </dl>
                <p className="note">
                  {t(
                    "DistilBERT مستبعد من المقارنة العادلة لاحتمال تداخل تدريبه السابق مع بيانات التحقق. يمكن الاطلاع على نتيجته التاريخية في التفاصيل أدناه.",
                    "DistilBERT is excluded from a fair ranking because its historical training may overlap the validation set. Its historical result is available in the details below.",
                  )}
                </p>
              </section>
              <section className="lab-section">
                <h2>
                  {t("البحث واستخراج المهام", "Retrieval & task extraction")}
                </h2>
                <div className="result-pair">
                  <div>
                    <span>Recall@5</span>
                    <strong>{pct(data.rag.qa.retrieval["recall@5"])}</strong>
                    <p>
                      {t(
                        "نسبة الرسائل المرجعية التي ظهرت ضمن أول خمس نتائج بحث.",
                        "Share of reference messages found in the top five search results.",
                      )}
                    </p>
                  </div>
                  <div>
                    <span>{t("F1 لاستخراج المهام", "Task extraction F1")}</span>
                    <strong>{data.rag.tasks?.f1.toFixed(2) ?? "—"}</strong>
                    <p>
                      {t(
                        "التوازن بين صحة المهام المستخرجة والعثور على المهام المتوقعة.",
                        "Balance between extracting correct tasks and finding expected tasks.",
                      )}
                    </p>
                  </div>
                </div>
                <p>
                  {t(
                    "نتائج بحثية من أسئلة ورسائل مؤلفة بمساعدة الذكاء الاصطناعي: 20 سؤالًا و16 رسالة لاختبار المهام. ليست مراجعة بشرية مستقلة أو مقياسًا عامًا لجودة البريد.",
                    "Research fixtures authored with AI assistance: 20 questions and 16 task-test messages. These are not independently human-reviewed or a general measure of email quality.",
                  )}
                </p>
                <p>
                  {t(
                    "Recall@5 يخص تجربة E5 الأصلية FP32، وليس قياسًا جديدًا لاسترجاع INT8 المنشور. بقي إخفاقان في مطابقة أدلة الإجابة. اختبار Linux اللاحق أكد عدم تغيّر نتائج الأسئلة والمهام أثناء تحسين الذاكرة؛ لا يحوّل ذلك هذه الأمثلة إلى تقييم جودة مستقل.",
                    "Recall@5 comes from the original FP32 E5 experiment, not a new retrieval measurement of the deployed INT8 model. Two answer-evidence mismatches remained. Later Linux qualification confirmed unchanged QA and task results during memory optimization; that does not make these fixtures an independent quality evaluation.",
                  )}
                </p>
              </section>
              <details className="research-details">
                <summary>
                  {t("تفاصيل المقاييس والأخطاء", "Detailed metrics & errors")}
                </summary>
                <label>
                  {t("اختر تجربة", "Inspect experiment")}
                  <select
                    value={candidate}
                    onChange={(e) => setCandidate(e.target.value)}
                  >
                    {data.models.map((m) => (
                      <option value={m.id} key={m.id}>
                        {names[m.id]}
                      </option>
                    ))}
                  </select>
                </label>
                {candidate === "B" && (
                  <p className="note">
                    {t(
                      "نتيجة تاريخية مستبعدة من اختيار النموذج: تقسيم التدريب الأصلي غير متاح.",
                      "Historical result excluded from selection: the original training split is unknown.",
                    )}
                  </p>
                )}
                <p>
                  <bdi>
                    Accuracy {pct(model.metrics.top1_accuracy)} · Macro F1{" "}
                    {model.metrics.top1_macro_f1.toFixed(3)} · Weighted F1{" "}
                    {model.metrics.top1_weighted_f1.toFixed(3)}
                  </bdi>
                </p>
                <p className="muted">
                  {t(
                    "Weighted F1 يزن نتيجة كل فئة بعدد أمثلتها.",
                    "Weighted F1 weights each category by its number of examples.",
                  )}
                </p>
                <div
                  className="lab-table"
                  role="region"
                  aria-label={t("أداء الفئات", "Per-class performance")}
                  tabIndex={0}
                >
                  <table>
                    <caption>{t("أداء كل فئة", "Per-class results")}</caption>
                    <thead>
                      <tr>
                        <th>{t("الفئة", "Category")}</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F1</th>
                        <th>n</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(model.metrics.per_class).map(
                        ([name, s]) => (
                          <tr key={name}>
                            <th>{categoryName(name, language)}</th>
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
                <p className="muted">
                  {t(
                    "Precision: كم من التنبؤات صحيح؟ Recall: كم من أمثلة الفئة عثر عليها النموذج؟ n: عدد الأمثلة المرجعية.",
                    "Precision: how many predictions are correct? Recall: how many reference examples are found? n: reference example count.",
                  )}
                </p>
                <details>
                  <summary>{t("مصفوفة الالتباس", "Confusion matrix")}</summary>
                  <p>
                    {t(
                      "الصفوف للوسوم المرجعية والأعمدة للتنبؤات. يُوزّع وزن الرسالة على وسومها عندما يكون لها أكثر من وسم.",
                      "Rows are reference labels and columns are predictions. Each message's weight is divided across its reference labels.",
                    )}
                  </p>
                  <div
                    className="lab-table"
                    tabIndex={0}
                    role="region"
                    aria-label={t("جدول الالتباس", "Confusion table")}
                  >
                    <table>
                      <thead>
                        <tr>
                          <th>
                            {t("المرجع / التنبؤ", "Reference / prediction")}
                          </th>
                          {labels.map((l) => (
                            <th key={l}>{categoryName(l, language)}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {model.metrics.confusion_matrix.map((row, i) => (
                          <tr key={labels[i]}>
                            <th>{categoryName(labels[i] ?? "", language)}</th>
                            {row.map((n, j) => (
                              <td
                                className={i === j ? "matrix-diagonal" : ""}
                                key={j}
                              >
                                {Number(n.toFixed(2))}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
                <p>
                  {t(
                    "عدد الأخطاء بدرجة نموذج 0.8 أو أعلى:",
                    "Incorrect predictions with a model score of at least 0.8:",
                  )}{" "}
                  {model.metrics.wrong_confident_ge_080}.{" "}
                  {t(
                    "الدرجات غير معايرة، ولا تمثل احتمالًا موثوقًا للصحة.",
                    "Scores are uncalibrated and are not reliable correctness probabilities.",
                  )}
                </p>
                <p>
                  {t(
                    "أظهرت الأخطاء التباسًا بين العروض والنشرات، وبين الدعم والشؤون المالية. لم أعدّل الوسوم لتحسين الأرقام.",
                    "Errors included confusion between promotions and newsletters, and between support and finance. I did not change labels to improve the scores.",
                  )}
                </p>
                <h3>
                  {t(
                    "قياس الأداء المحلي التاريخي",
                    "Historical local performance",
                  )}
                </h3>
                <p>
                  <bdi>
                    p95 {model.run.benchmark.p95_ms.toFixed(1)} ms ·{" "}
                    {model.run.benchmark.process_peak_wset_mib.toFixed(2)} MiB
                  </bdi>
                </p>
                <p className="muted">
                  {t(
                    "قياس Windows على 30 رسالة بعد الإحماء؛ p95 هو الزمن الذي انتهت خلاله 95% من الطلبات. ذروة العملية تشمل التحميل والتدريب. ليست هذه متطلبات الاستضافة أو ذروة Linux.",
                    "Windows measurements on 30 warmed messages; p95 is the time within which 95% of requests finished. Process peak includes loading/training. These are not hosting requirements or Linux peak measurements.",
                  )}
                </p>
                <h3>
                  {t(
                    "تشخيص DistilBERT السابق",
                    "Historical DistilBERT diagnostics",
                  )}
                </h3>
                <p>
                  {t(
                    "لم يجتز معيار الجودة. على 100 مثال تطويري صعب سبق استخدامه:",
                    "The quality gate failed. On 100 difficult, previously used development examples:",
                  )}{" "}
                  <bdi>
                    {Math.round(
                      data.historical.development.top1_accuracy *
                        data.historical.development.n,
                    )}
                    /{data.historical.development.n} · Macro F1{" "}
                    {data.historical.development.top1_macro_f1.toFixed(4)}
                  </bdi>
                </p>
                <ul>
                  {Object.entries(data.historical.languages).map(
                    ([name, s]) => (
                      <li key={name}>
                        {name === "English"
                          ? t("الإنجليزية", "English")
                          : t("نصوص يغلب عليها العربي", "Arabic-heavy")}
                        :{" "}
                        <bdi>
                          {s.correct}/{s.n}
                        </bdi>
                      </li>
                    ),
                  )}
                </ul>
                <p className="muted">
                  {t(
                    "شرائح صغيرة محددة آليًا حسب اللغة، ومن مجموعة مختلفة عن جدول التحقق أعلاه. لا تصلح هذه الأرقام للمقارنة المباشرة أو لتقدير الدقة العامة.",
                    "Small, heuristically labelled language slices from a different dataset than the validation table above. These figures do not support direct comparisons or general accuracy claims.",
                  )}
                </p>
              </details>
            </>
          )}
          {section === "playground" && (
            <Intelligence key={email.id} email={email} />
          )}
          <aside className="lab-limits">
            <h2>{t("حدود التجربة", "Limitations")}</h2>
            <p>
              {t(
                "النتائج المعروضة توضح أداء النماذج ضمن التجارب التي أجريتها، ولا تعني أنها جاهزة للاستخدام الفعلي على نطاق واسع.",
                "These results describe the models within my experiments; they do not establish readiness for large-scale real-world use.",
              )}
            </p>
            <p>
              {t(
                "لم يُقيّم المصنّف المختار على العربية، ولا يتوفر اختبار نهائي مستقل. أدلة البحث والمهام أمثلة بحثية محدودة.",
                "The selected classifier has not been evaluated on Arabic, and no independent final test is available. Retrieval and task evidence comes from limited research fixtures.",
              )}
            </p>
          </aside>
          <div className="lab-sources">
            <span>{t("توثيق التجارب:", "Experiment records:")}</span>
            <a
              href={repo + "docs/phase2/README.md"}
              target="_blank"
              rel="noreferrer"
            >
              {t("التصنيف والبيانات", "Classification & data")}
            </a>
            <a
              href={repo + "docs/release/V03_V10_EVIDENCE.md"}
              target="_blank"
              rel="noreferrer"
            >
              {t("التجارب السابقة", "Historical experiments")}
            </a>
            <a
              href={repo + "docs/phase3/README.md"}
              target="_blank"
              rel="noreferrer"
            >
              {t("البحث والمهام", "Retrieval & tasks")}
            </a>
          </div>
        </div>
      )}
    </section>
  );
}
