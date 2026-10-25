import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Inbox } from "lucide-react";
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
import { RetroWindow } from "../../components/ui/RetroWindow";

export function InboxPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const [params, setParams] = useSearchParams();
  const filters = readInboxState(params);
  const query = useQuery({
    queryKey: keys.list(filters),
    queryFn: ({ signal }) => emails.list(api, filters, signal),
  });
  const filtered = !!filters.categories?.length || !!filters.priority_level;
  function change(key: string, value: string | string[]) {
    const next = new URLSearchParams(params);
    next.delete("offset");
    next.delete(key);
    if (Array.isArray(value)) value.forEach((item) => next.append(key, item));
    else if (value) next.set(key, value);
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
    <div className="flex flex-col gap-4">
      <div className="page-heading">
        <div>
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
      <RetroWindow
        title={t("البريد الوارد", "Inbox")}
        icon={<Inbox size={16} className="text-[#E07A5F]" />}
      >
        <section
          className="surface border-0 rounded-none shadow-none"
          aria-label={t("قائمة البريد", "Email list")}
        >
          <InboxToolbar filters={filters} change={change} />
          {query.isPending ? (
            <EmailSkeleton />
          ) : query.isError ? (
            <ErrorState
              error={query.error}
              retry={() => void query.refetch()}
            />
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
              <div className="center p-4">
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
      </RetroWindow>
    </div>
  );
}
