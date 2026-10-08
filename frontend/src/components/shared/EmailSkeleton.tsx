import { useLocale } from "../../app/locale";
export function EmailSkeleton({ detail = false }: { detail?: boolean }) {
  const { t } = useLocale();
  return (
    <div
      role="status"
      aria-label={t("جارٍ التحميل…", "Loading…")}
      className={detail ? "detail-skeleton" : "inbox-skeleton"}
    >
      <span className="sr-only">{t("جارٍ التحميل…", "Loading…")}</span>
      {(detail ? [1, 2, 3] : [1, 2, 3, 4]).map((n) => (
        <div className="skeleton-row" key={n} aria-hidden="true">
          <div className="skeleton skeleton-short" />
          <div className="skeleton" />
          <div className="skeleton skeleton-medium" />
        </div>
      ))}
    </div>
  );
}
