import { Link } from "react-router-dom";
import type { AskAnswer } from "../../api/ask";
import { useLocale } from "../../app/locale";
import { EmailDate } from "../../components/ui/EmailDate";
export const safeText = (value: unknown) =>
  typeof value === "string" ? value : "";
export function SourceList({ sources }: { sources: AskAnswer["sources"] }) {
  const { t } = useLocale();
  return (
    <section className="source-section">
      <h3>{t("ارجع إلى المصدر", "Return to the source")}</h3>
      {sources.length ? (
        <ul className="source-cards">
          {sources.map((source) => (
            <li key={source.email_id}>
              <Link to={"/email/" + source.email_id}>
                <strong dir="auto">
                  {safeText(source.subject) ||
                    t("بريد بلا عنوان", "Untitled email")}
                </strong>
                <span dir="auto" className="muted">
                  {safeText(source.from)}
                </span>
                <EmailDate value={safeText(source.date)} />
                <span className="source-action">
                  {t("فتح البريد", "Open email")}{" "}
                  <bdi dir="ltr">#{source.email_id}</bdi>
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
    </section>
  );
}
