import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { emails } from "../../api/emails";
import { keys } from "../../app/query";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Empty, ErrorState } from "../../components/shared/States";
import { EmailSkeleton } from "../../components/shared/EmailSkeleton";
import { EmailList } from "./EmailList";
import { InboxToolbar } from "./InboxToolbar";
import { Pagination } from "./Pagination";
import { readInboxState } from "./inboxState";
export function InboxPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const [params, setParams] = useSearchParams();
  const filters = readInboxState(params);
  const query = useQuery({
    queryKey: keys.list(filters),
    queryFn: ({ signal }) => emails.list(api, filters, signal),
  });
  const filtered =
    !!filters.category ||
    !!filters.priority_level ||
    filters.has_tasks !== undefined ||
    filters.has_deadline !== undefined;
  function change(key: string, value: string) {
    const next = new URLSearchParams(params);
    next.delete("offset");
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }
  function clear() {
    const next = new URLSearchParams(params);
    for (const key of ["priority", "category", "tasks", "deadline", "offset"])
      next.delete(key);
    setParams(next);
  }
  function page(offset: number) {
    const next = new URLSearchParams(params);
    next.set("offset", String(offset));
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
              "رسائلك ومهامك، بصورة أوضح.",
              "Your messages and next steps, at a glance.",
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
        <InboxToolbar
          key={params.toString()}
          filters={filters}
          change={change}
          clear={clear}
        />
        {query.isPending ? (
          <EmailSkeleton />
        ) : query.isError ? (
          <ErrorState error={query.error} retry={() => void query.refetch()} />
        ) : query.data.emails.length ? (
          <EmailList items={query.data.emails} />
        ) : (
          <>
            <Empty
              title={
                filtered
                  ? t("لا توجد رسائل تطابق الفلاتر", "No matching emails")
                  : query.data.total
                    ? t("هذه الصفحة فارغة", "This page is empty")
                    : t("لا توجد رسائل هنا", "No emails here")
              }
              detail={
                filtered
                  ? t("جرّب إزالة بعض الفلاتر.", "Try removing some filters.")
                  : t(
                      "يمكنك مزامنة حسابك من الإعدادات.",
                      "You can sync your account in Settings.",
                    )
              }
            />
            <div className="center">
              <button onClick={filtered ? clear : () => page(0)}>
                {filtered
                  ? t("مسح الفلاتر", "Clear filters")
                  : t("الصفحة الأولى", "First page")}
              </button>
            </div>
          </>
        )}
        {query.data && !query.isError && (
          <Pagination
            offset={filters.offset || 0}
            limit={query.data.limit}
            count={query.data.count}
            total={query.data.total}
            busy={query.isFetching}
            change={page}
          />
        )}
      </section>
    </>
  );
}
