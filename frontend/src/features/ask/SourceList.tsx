import { Link } from "react-router-dom";
import type { AskAnswer } from "../../api/ask";
import { useLocale } from "../../app/locale";
import { readableDate } from "./presentation";
export const safeText = (value: unknown) =>
  typeof value === "string" ? value : "";
export function SourceList({ sources }: { sources: AskAnswer["sources"] }) {
  const { t, language } = useLocale();
  return (
    <details className="source-section">
      <summary>
        {t("المصادر", "Sources")} ({sources.length})
      </summary>
      {sources.length ? (
        <ul className="source-cards">
          {sources.map((source) => (
            <li key={source.email_id}>
              <Link
                to={"/email/" + source.email_id}
                state={{ returnTo: "/ask" }}
              >
                <strong dir="auto">
                  {safeText(source.subject) ||
                    t("بريد بلا عنوان", "Untitled email")}
                </strong>
                <span dir="auto" className="muted">
                  {safeText(source.from)}
                </span>
                <span>
                  {readableDate(safeText(source.date), language) ||
                    t("التاريخ غير متاح", "Date unavailable")}
                </span>
                <span className="source-action">
                  {t("فتح البريد", "Open email")}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">
          {t(
            "لا تتوفر روابط مصادر متطابقة لهذه الإجابة.",
            "No matching source links are available for this answer.",
          )}
        </p>
      )}
    </details>
  );
}
