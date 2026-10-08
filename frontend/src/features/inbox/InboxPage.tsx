import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { emails, type InboxFilters } from "../../api/emails";
import { keys } from "../../app/query";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Loading, Empty, ErrorState } from "../../components/shared/States";
import { EmailList } from "./EmailList";
export function InboxPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const [params, setParams] = useSearchParams();
  const parsed = Number(params.get("offset") || 0);
  const offset = Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : 0;
  const priority = params.get("priority");
  const sort = params.get("sort");
  const filters: InboxFilters = {
    limit: 20,
    offset,
    priority_level:
      priority === "high" || priority === "medium" || priority === "low"
        ? priority
        : undefined,
    has_tasks: params.get("tasks") === "true" ? true : undefined,
    has_deadline: params.get("deadline") === "true" ? true : undefined,
    category: params.get("category") || undefined,
    sort_by: sort === "priority_score" ? "priority_score" : "created_at",
    sort_order: params.get("order") === "asc" ? "asc" : "desc",
  };
  const query = useQuery({
    queryKey: keys.list(filters),
    queryFn: ({ signal }) => emails.list(api, filters, signal),
  });
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params);
    next.delete("offset");
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }
  function page(value: number) {
    const next = new URLSearchParams(params);
    next.set("offset", String(value));
    setParams(next);
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">INBOX</p>
          <h1>{t("البريد الوارد", "Inbox")}</h1>
          <p>
            {t(
              "كل ما يهمك، في مكان أوضح.",
              "Everything that matters, with a little more clarity.",
            )}
          </p>
        </div>
        {query.data && (
          <span className="count">
            {query.data.total} {t("رسالة", "messages")}
          </span>
        )}
      </div>
      <section className="surface" aria-label={t("قائمة البريد", "Email list")}>
        <div className="filters">
          <label>
            {t("الأولوية", "Priority")}
            <select
              value={priority || ""}
              onChange={(e) => filter("priority", e.target.value)}
            >
              <option value="">{t("الكل", "All")}</option>
              <option value="high">{t("عالية", "High")}</option>
              <option value="medium">{t("متوسطة", "Medium")}</option>
              <option value="low">{t("منخفضة", "Low")}</option>
            </select>
          </label>
          <label>
            {t("الترتيب", "Sort")}
            <select
              value={sort || "created_at"}
              onChange={(e) => filter("sort", e.target.value)}
            >
              <option value="created_at">
                {t("تاريخ الإضافة", "Date added")}
              </option>
              <option value="priority_score">
                {t("درجة الأولوية", "Priority score")}
              </option>
            </select>
          </label>
          <label>
            {t("الاتجاه", "Order")}
            <select
              value={params.get("order") || "desc"}
              onChange={(e) => filter("order", e.target.value)}
            >
              <option value="desc">{t("تنازلي", "Descending")}</option>
              <option value="asc">{t("تصاعدي", "Ascending")}</option>
            </select>
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={!!filters.has_tasks}
              onChange={(e) => filter("tasks", e.target.checked ? "true" : "")}
            />
            {t("بمهام", "Has tasks")}
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={!!filters.has_deadline}
              onChange={(e) =>
                filter("deadline", e.target.checked ? "true" : "")
              }
            />
            {t("بموعد نهائي", "Has deadline")}
          </label>
        </div>
        {query.isPending ? (
          <Loading />
        ) : query.isError ? (
          <ErrorState error={query.error} retry={() => void query.refetch()} />
        ) : query.data.emails.length ? (
          <EmailList items={query.data.emails} />
        ) : (
          <Empty
            title={t("لا توجد رسائل هنا", "No emails here")}
            detail={t(
              "جرّب تغيير عوامل التصفية أو مزامنة حسابك من الإعدادات.",
              "Try different filters or sync your account in Settings.",
            )}
          />
        )}
        <div className="pagination">
          <button
            disabled={offset === 0 || query.isFetching}
            onClick={() => page(Math.max(0, offset - 20))}
          >
            {t("السابق", "Previous")}
          </button>
          <span>
            {t("صفحة", "Page")} {Math.floor(offset / 20) + 1}
          </span>
          <button
            disabled={
              !query.data || offset + 20 >= query.data.total || query.isFetching
            }
            onClick={() => page(offset + 20)}
          >
            {t("التالي", "Next")}
          </button>
        </div>
      </section>
    </>
  );
}
