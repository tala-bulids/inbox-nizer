import { useLocale } from "../../app/locale";
export function formatEmailDate(
  value: string,
  language: string,
): string | null {
  // Only normalized timestamps and calendar dates are parsed. Raw headers stay raw.
  if (
    !/^\d{4}-\d{2}-\d{2}(?:$|T\d{2}:\d{2}.*(?:Z|[+-]\d{2}:\d{2})$)/.test(value)
  )
    return null;
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return null;
  const dayOnly = value.length === 10;
  return new Intl.DateTimeFormat(
    language === "ar" ? "ar-SA-u-ca-gregory" : "en-GB",
    {
      dateStyle: "medium",
      ...(dayOnly ? { timeZone: "UTC" } : { timeStyle: "short" }),
    },
  ).format(date);
}
export function EmailDate({ value }: { value: string }) {
  const { language, t } = useLocale();
  const formatted = formatEmailDate(value, language);
  if (!value)
    return (
      <span className="muted">{t("التاريخ غير متاح", "Date unavailable")}</span>
    );
  return (
    <time dateTime={formatted ? value : undefined} title={value}>
      <bdi dir={formatted ? "auto" : "ltr"}>{formatted || value}</bdi>
    </time>
  );
}
