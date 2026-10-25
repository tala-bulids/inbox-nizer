import { useLocale } from "../../app/locale";
export function Pagination({
  offset,
  limit,
  count,
  total,
  busy,
  change,
}: {
  offset: number;
  limit: number;
  count: number;
  total: number;
  busy: boolean;
  change: (offset: number) => void;
}) {
  const { t } = useLocale();
  return (
    <div
      className="pagination"
      aria-label={t("صفحات البريد", "Inbox pagination")}
    >
      <button
        disabled={offset === 0 || busy}
        onClick={() => change(Math.max(0, offset - limit))}
      >
        {t("السابق", "Previous")}
      </button>
      <span aria-live="polite">
        {count ? offset + 1 : 0}–{count ? offset + count : 0} {t("من", "of")}{" "}
        {total}
      </span>
      <button
        disabled={busy || offset + limit >= total}
        onClick={() => change(offset + limit)}
      >
        {t("التالي", "Next")}
      </button>
    </div>
  );
}
