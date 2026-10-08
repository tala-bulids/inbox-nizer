import { Link } from "react-router-dom";
import { ArrowUpLeft, Paperclip } from "lucide-react";
import type { Email } from "../../api/contracts";
import { useLocale } from "../../app/locale";
import { Identifier } from "../../components/ui/Text";
export function EmailList({ items }: { items: Email[] }) {
  const { t } = useLocale();
  return (
    <ul className="email-list">
      {items.map((email) => (
        <li key={email.id}>
          <Link to={`/email/${email.id}`} className="email-row">
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
                <time>
                  <Identifier>{email.date}</Identifier>
                </time>
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
                    {email.priority_level}
                  </span>
                )}
                {email.predictions.map((p, i) => (
                  <span className="badge" key={i} dir="auto">
                    {p.category}
                  </span>
                ))}
                {email.tasks.length > 0 && (
                  <span className="badge">
                    <Paperclip size={12} />
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
