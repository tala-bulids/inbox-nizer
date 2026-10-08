import { Link, useParams, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { keys } from "../../app/query";
import { emails } from "../../api/emails";
import { validId } from "../../api/ask";
import { Empty, ErrorState } from "../../components/shared/States";
import { ContentText } from "../../components/ui/Text";
import { EmailDate } from "../../components/ui/EmailDate";
import { EmailSkeleton } from "../../components/shared/EmailSkeleton";
import { EmailTasks } from "./EmailTasks";
import { inboxReturnPath } from "../inbox/inboxState";
export function EmailPage() {
  const id = Number(useParams().id);
  const location = useLocation();
  const back = inboxReturnPath(
    (location.state as { inbox?: unknown } | null)?.inbox,
  );
  const { api } = useAuth();
  const { t } = useLocale();
  const query = useQuery({
    queryKey: keys.detail(id),
    queryFn: ({ signal }) => emails.detail(api, id, signal),
    enabled: validId(id),
  });
  if (!validId(id))
    return <Empty title={t("معرّف بريد غير صالح", "Invalid email ID")} />;
  const backLink = (
    <Link to={back} className="back-link">
      {t("العودة إلى البريد الوارد", "Back to inbox")}
    </Link>
  );
  if (query.isPending)
    return (
      <>
        {backLink}
        <EmailSkeleton detail />
      </>
    );
  if (query.isError)
    return (
      <>
        {backLink}
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      </>
    );
  const email = query.data;
  return (
    <article className="detail">
      {backLink}
      <div className="page-heading">
        <div>
          <p className="eyebrow">EMAIL</p>
          <h1 dir="auto">{email.subject || t("بلا عنوان", "No subject")}</h1>
          <p>
            <bdi dir="auto">
              {email.from || t("مرسل غير معروف", "Unknown sender")}
            </bdi>
          </p>
          <small>
            {email.sent_at
              ? t("تاريخ إرسال البريد: ", "Email sent: ")
              : t("تاريخ رسالة البريد: ", "Email message date: ")}
            <EmailDate
              value={email.sent_at || email.message_at || email.date}
            />
          </small>
        </div>
      </div>
      {email.processing.some(
        (item) => item.status === "failed" || item.status === "pending",
      ) && (
        <p className="processing-notice" role="status">
          {t(
            "بعض المعلومات المساعدة غير متاحة بعد. يمكنك قراءة نص البريد أدناه.",
            "Some derived information is not available yet. You can still read the email below.",
          )}
        </p>
      )}
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
            <span className="badge" key={i} dir="auto">
              {p.category}
            </span>
          ))}
        </div>
        <h3>{t("ملخص آلي", "AI summary")}</h3>
        <ContentText>
          {email.summary || t("لا يوجد ملخص", "No summary available")}
        </ContentText>
        <EmailTasks tasks={email.tasks} />
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
