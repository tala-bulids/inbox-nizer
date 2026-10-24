import { Link, useParams, useLocation } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Mail, ArrowLeft, ArrowRight } from "lucide-react";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { categoryLabel } from "../../app/categoryLabels";
import { keys } from "../../app/query";
import { emails } from "../../api/emails";
import { validId } from "../../api/ask";
import { Empty, ErrorState } from "../../components/shared/States";
import { ContentText } from "../../components/ui/Text";
import { EmailDate } from "../../components/ui/EmailDate";
import { EmailSkeleton } from "../../components/shared/EmailSkeleton";
import { EmailTasks } from "./EmailTasks";
import { emailReturnPath } from "../inbox/inboxState";
import { RetroWindow } from "../../components/ui/RetroWindow";
export function EmailPage() {
  const id = Number(useParams().id);
  const location = useLocation();
  const state = location.state as {
    returnTo?: unknown;
    inbox?: unknown;
  } | null;
  const back = emailReturnPath(state?.returnTo ?? state?.inbox);
  const { api } = useAuth();
  const { t, language } = useLocale();
  const isEn = language === "en";
  const qc = useQueryClient();
  const retry = useMutation({
    mutationFn: () => emails.retryEnrichment(api, id),
    retry: false,
    onSettled: async () => {
      await Promise.all(
        [keys.emails, keys.accounts, keys.tasks].map((queryKey) =>
          qc.invalidateQueries({ queryKey }),
        ),
      );
    },
  });
  const query = useQuery({
    queryKey: keys.detail(id),
    queryFn: ({ signal }) => emails.detail(api, id, signal),
    enabled: validId(id),
  });
  if (!validId(id))
    return <Empty title={t("معرّف بريد غير صالح", "Invalid email ID")} />;
  const backLink = (
    <Link
      to={back}
      className="back-link inline-flex items-center gap-1.5 font-mono-code text-xs"
    >
      {isEn ? <ArrowLeft size={14} /> : <ArrowRight size={14} />}
      <span>
        {back === "/search"
          ? t("العودة إلى البحث", "Back to search")
          : back === "/ask"
            ? t("العودة إلى الإجابة", "Back to answer")
            : back.startsWith("/tasks")
              ? t("العودة إلى المهام", "Back to tasks")
              : t("العودة إلى البريد الوارد", "Back to inbox")}
      </span>
    </Link>
  );
  if (query.isPending)
    return (
      <div className="flex flex-col gap-4">
        {backLink}
        <EmailSkeleton detail />
      </div>
    );
  if (query.isError)
    return (
      <div className="flex flex-col gap-4">
        {backLink}
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      </div>
    );
  const email = query.data;
  return (
    <RetroWindow
      title={t("تفاصيل البريد", "Email detail")}
      subtitle={email.subject || undefined}
      icon={<Mail size={16} className="text-[#E07A5F]" />}
      toolbar={
        <div className="w-full flex items-center justify-between">
          {backLink}
        </div>
      }
    >
      <article className="detail p-4 sm:p-6">
        <div className="page-heading">
          <div>
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
        {email.processing.some(
          (item) => item.status === "failed" || item.status === "pending",
        ) && (
          <div>
            <button disabled={retry.isPending} onClick={() => retry.mutate()}>
              {retry.isPending
                ? t("جاري إعادة المعالجة…", "Retrying…")
                : t(
                    "إعادة معالجة المعلومات المساعدة",
                    "Retry derived information",
                  )}
            </button>
            <p className="muted">
              {t(
                "محاولة واحدة لهذه الرسالة. إذا استمر الفشل، حاول بعد إصلاح الخدمة. نص البريد محفوظ.",
                "One attempt for this email. If it still fails, retry after the service is repaired. Stored email is preserved.",
              )}
            </p>
            {retry.isError && <ErrorState error={retry.error} />}
          </div>
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
              {t("الأولوية", "Priority")}:{" "}
              {email.priority_level === "high"
                ? t("عالية", "High")
                : email.priority_level === "medium"
                  ? t("متوسطة", "Medium")
                  : email.priority_level === "low"
                    ? t("منخفضة", "Low")
                    : email.priority_level || "—"}
            </span>
            {email.predictions.map((p, i) => (
              <span className="badge" key={i} dir="auto">
                {categoryLabel(p.category, language)}
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
            <h2>
              {t("نص البريد الأصلي المخزن", "Stored original email text")}
            </h2>
            <span className="badge">{t("المصدر", "Source")}</span>
          </div>
          <ContentText>
            {email.body || t("لا يوجد محتوى نصي", "No text content")}
          </ContentText>
        </section>
      </article>
    </RetroWindow>
  );
}
