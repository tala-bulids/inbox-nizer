import { Link, useLocation } from "react-router-dom";
import { ArrowUpLeft, ListChecks } from "lucide-react";
import type { Email } from "../../api/contracts";
import { useLocale } from "../../app/locale";
import { categoryLabel } from "../../app/categoryLabels";
import { EmailDate } from "../../components/ui/EmailDate";
export function EmailList({ items }: { items: Email[] }) {
  const { t, language } = useLocale();
  const location = useLocation();
  return (
    <ul className="email-list">
      {items.map((email) => (
        <li key={email.id}>
          <Link
            to={`/email/${email.id}`}
            className="email-row"
            state={{ returnTo: location.pathname + location.search }}
          >
            <span className="avatar" aria-hidden="true">
              {(email.from || email.subject || "@")
                .replace(/["<]/g, "")
                .trim()
                .slice(0, 1)}
            </span>
            <div className="email-main">
              <div className="email-meta">
                <strong dir="auto">
                  {email.from || t("مرسل غير معروف", "Unknown sender")}
                </strong>
                <EmailDate
                  value={email.sent_at || email.message_at || email.date}
                />
              </div>
              <h2 dir="auto">
                {email.subject || t("بلا عنوان", "No subject")}
              </h2>
              {email.summary && (
                <p dir="auto" className="preview">
                  {email.summary}
                </p>
              )}
              <div className="tags">
                {email.priority_level && (
                  <span
                    className={`badge priority-${["high", "medium", "low"].includes(email.priority_level) ? email.priority_level : "low"}`}
                  >
                    {t("الأولوية: ", "Priority: ")}
                    {email.priority_level === "high"
                      ? t("عالية", "High")
                      : email.priority_level === "medium"
                        ? t("متوسطة", "Medium")
                        : email.priority_level === "low"
                          ? t("منخفضة", "Low")
                          : email.priority_level}
                  </span>
                )}
                {email.predictions
                  .filter((p) => p.category)
                  .slice(0, 2)
                  .map((p, i) => (
                    <span className="badge" key={i} dir="auto">
                      {categoryLabel(p.category, language)}
                    </span>
                  ))}
                {email.predictions.filter((p) => p.category).length > 2 && (
                  <span
                    className="badge"
                    title={email.predictions
                      .slice(2)
                      .map((p) => categoryLabel(p.category, language))
                      .join(t("، ", ", "))}
                  >
                    +{email.predictions.filter((p) => p.category).length - 2}{" "}
                    {t("تصنيفات", "categories")}
                  </span>
                )}
                {email.tasks.length > 0 && (
                  <span className="badge">
                    <ListChecks size={12} aria-hidden="true" />
                    {email.tasks.length} {t("مهام مستخرجة", "extracted tasks")}
                  </span>
                )}
                {email.tasks.some(
                  (task) =>
                    task.deadline_text ||
                    task.deadline_date ||
                    task.deadline_at,
                ) && (
                  <span className="badge">
                    {t("يوجد موعد نهائي", "Has deadline")}
                  </span>
                )}
              </div>
            </div>
            <ArrowUpLeft size={16} className="row-arrow" aria-hidden="true" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
