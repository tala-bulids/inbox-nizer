import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { keys } from "../../app/query";
import { emails } from "../../api/emails";
import { validId } from "../../api/ask";
import { Loading, Empty, ErrorState } from "../../components/shared/States";
import { ContentText, Identifier } from "../../components/ui/Text";
export function EmailPage() {
  const id = Number(useParams().id);
  const { api } = useAuth();
  const { t } = useLocale();
  const query = useQuery({
    queryKey: keys.detail(id),
    queryFn: ({ signal }) => emails.detail(api, id, signal),
    enabled: validId(id),
  });
  if (!validId(id))
    return <Empty title={t("معرّف بريد غير صالح", "Invalid email ID")} />;
  if (query.isPending) return <Loading />;
  if (query.isError) return <ErrorState error={query.error} />;
  const email = query.data;
  return (
    <article className="detail">
      <Link to="/" className="back-link">
        ← {t("البريد الوارد", "Inbox")}
      </Link>
      <div className="page-heading">
        <div>
          <p className="eyebrow">EMAIL</p>
          <h1 dir="auto">{email.subject || t("بلا عنوان", "No subject")}</h1>
          <p>
            <Identifier>{email.from}</Identifier>
          </p>
          <small>
            <Identifier>{email.date}</Identifier>
          </small>
        </div>
      </div>
      <section className="derived">
        <h2>
          {t(
            "معلومات مستخرجة ومساعدة آلية",
            "Extracted information & AI assistance",
          )}
        </h2>
        <p className="muted">
          {t(
            "راجع النص الأصلي. الملخص والتصنيف ليسا حقائق متحققة بشكل مستقل.",
            "Check the original. Summaries and classifications are not independently verified facts.",
          )}
        </p>
        <div className="tags">
          <span className="badge">
            {t("الأولوية", "Priority")}: {email.priority_level || "—"}
          </span>
          {email.predictions.map((p, i) => (
            <span className="badge" key={i}>
              {p.category}
            </span>
          ))}
        </div>
        <h3>{t("ملخص آلي", "AI summary")}</h3>
        <ContentText>
          {email.summary || t("لا يوجد ملخص", "No summary available")}
        </ContentText>
        <h3>
          {t("المهام والمواعيد المستخرجة", "Extracted tasks & deadlines")}
        </h3>
        {email.tasks.length ? (
          <ul className="task-list">
            {email.tasks.map((task, i) => (
              <li key={i}>
                <ContentText>{task.task}</ContentText>
                <Identifier>
                  {task.deadline_text || task.deadline_date || task.deadline_at}
                </Identifier>
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("لا توجد مهام مستخرجة", "No extracted tasks")}</p>
        )}
        <p className="muted">
          {t(
            "عرض الحقائق المنظمة ينتظر API مخصصًا.",
            "Structured-fact browsing awaits a dedicated API.",
          )}
        </p>
      </section>
      <section className="original">
        <div className="section-heading">
          <h2>{t("نص البريد الأصلي المخزن", "Stored original email text")}</h2>
          <span className="badge">{t("المصدر", "Source")}</span>
        </div>
        <ContentText>
          {email.body || t("لا يوجد محتوى نصي", "No text content")}
        </ContentText>
      </section>
    </article>
  );
}
