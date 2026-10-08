import { Link } from "react-router-dom";
import { ShieldCheck, TriangleAlert } from "lucide-react";
import type { AskAnswer } from "../../api/ask";
import { validId } from "../../api/ask";
import { useLocale } from "../../app/locale";
import { ContentText, Identifier } from "../../components/ui/Text";
import { Empty } from "../../components/shared/States";
const text = (value: unknown) => (typeof value === "string" ? value : "");
export function AnswerView({
  answer,
  onClarify,
}: {
  answer: AskAnswer;
  onClarify: (id: number) => void;
}) {
  const { t } = useLocale();
  if (answer.status === "insufficient_evidence")
    return (
      <Empty
        title={t("لا توجد أدلة كافية", "Insufficient evidence")}
        detail={answer.answer}
      />
    );
  if (answer.status === "needs_clarification")
    return (
      <section className="answer-panel">
        <h2>{t("لنحدد البريد المقصود", "Which email do you mean?")}</h2>
        <ContentText>{answer.answer}</ContentText>
        <div className="clarification-options">
          {Array.isArray(answer.clarification_options) &&
            answer.clarification_options
              .filter((o) => o && validId(o.email_id))
              .slice(0, 5)
              .map((option) => (
                <button
                  key={option.email_id}
                  onClick={() => onClarify(option.email_id)}
                >
                  <strong dir="auto">
                    {text(option.subject) ||
                      t("بريد بلا عنوان", "Untitled email")}
                  </strong>
                  <Identifier>{text(option.date)}</Identifier>
                </button>
              ))}
        </div>
        <p className="muted">
          {t(
            "يمكنك أيضًا إضافة اسم الجهة أو الموعد إلى سؤالك.",
            "You can also add an organization or date to your question.",
          )}
        </p>
      </section>
    );
  const supported =
    answer.verification === "source_supported" &&
    (answer.answer_mode === "deterministic_fact" ||
      answer.answer_mode === "extractive");
  const generated =
    answer.answer_mode === "generated_synthesis" ||
    answer.verification === "not_semantically_verified";
  const cited = new Set(
    answer.citations
      .filter((c) => c && validId(c.email_id))
      .map((c) => c.email_id),
  );
  const sources = answer.sources.filter(
    (s) => s && validId(s.email_id) && cited.has(s.email_id),
  );
  return (
    <section
      className={`answer-panel ${supported ? "supported" : "unverified"}`}
    >
      <div
        className={supported ? "answer-label" : "synthesis-warning"}
        role={supported ? undefined : "note"}
      >
        {supported ? (
          <>
            <ShieldCheck size={19} />
            <strong>{t("مدعوم من البريد", "Source-supported")}</strong>
            <span>
              {t(
                "ليس تحققًا مستقلًا من الحقيقة",
                "Not independently verified truth",
              )}
            </span>
          </>
        ) : (
          <>
            <TriangleAlert size={22} />
            <div>
              <strong>
                {generated
                  ? t(
                      "صياغة مولّدة بالذكاء الاصطناعي",
                      "Generated AI synthesis",
                    )
                  : t("حالة التحقق غير معروفة", "Verification unknown")}
              </strong>
              <p>
                {t(
                  "قد يُسقط النص شروطًا أو نفيًا أو استثناءات. راجع البريد الأصلي قبل الاعتماد عليه.",
                  "May omit conditions, negation or exceptions. Review the original email before relying on it.",
                )}
              </p>
            </div>
          </>
        )}
      </div>
      <ContentText>{answer.answer}</ContentText>
      <dl className="verification-meta">
        <dt>{t("المسار", "Mode")}</dt>
        <dd>
          <Identifier>{text(answer.answer_mode) || "unknown"}</Identifier>
        </dd>
        <dt>{t("التحقق", "Verification")}</dt>
        <dd>
          <Identifier>{text(answer.verification) || "unknown"}</Identifier>
        </dd>
      </dl>
      <h3>{t("ارجع إلى المصدر", "Return to the source")}</h3>
      <ul className="sources">
        {sources.map((source) => (
          <li key={`${source.email_id}-${source.chunk_id}`}>
            <Link to={`/email/${source.email_id}`}>
              <span dir="auto">
                {text(source.subject) || t("فتح البريد", "Open email")}
              </span>
              <small>
                <Identifier>{text(source.date)}</Identifier>
              </small>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
