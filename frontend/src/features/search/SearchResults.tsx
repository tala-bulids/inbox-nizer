import { Link } from "react-router-dom";
import type { SearchResult } from "../../api/contracts";
import { useLocale } from "../../app/locale";
export function SearchResults({ items }: { items: SearchResult[] }) {
  const { t } = useLocale();
  return (
    <ol className="result-list search-results">
      {items.map((item, index) => (
        <li key={item.email.id}>
          <Link to={"/email/" + item.email.id}>
            <span className="result-rank">
              {t("نتيجة", "Result")} {index + 1}
            </span>
            <h2 dir="auto">
              {item.email.subject || t("بلا عنوان", "No subject")}
            </h2>
            <p className="muted" dir="auto">
              {item.email.from || t("مرسل غير معروف", "Unknown sender")}
            </p>
            <p className="snippet-label">
              {t("مقطع مطابق من البريد", "Matching email excerpt")}
            </p>
            <p className="matched-text" dir="auto">
              {item.matched_text ||
                t(
                  "المقطع غير متاح؛ افتح البريد لقراءة المحتوى.",
                  "Excerpt unavailable; open the email to read it.",
                )}
            </p>
            <span className="source-action">
              {t("فتح البريد", "Open email")}
            </span>
          </Link>
        </li>
      ))}
    </ol>
  );
}
