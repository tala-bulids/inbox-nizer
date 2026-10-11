import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ListChecks } from "lucide-react";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { listTasks, type TaskFilters } from "../../api/tasks";
import { keys } from "../../app/query";
import { EmailSkeleton } from "../../components/shared/EmailSkeleton";
import { Empty, ErrorState } from "../../components/shared/States";
import { EmailDate } from "../../components/ui/EmailDate";
import { ContentText } from "../../components/ui/Text";
import { RetroWindow } from "../../components/ui/RetroWindow";
export function TasksPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const [params, setParams] = useSearchParams();
  const n = Number(params.get("offset") || 0);
  const offset =
    Number.isSafeInteger(n) && n >= 0 && n < Number.MAX_SAFE_INTEGER - 100
      ? n
      : 0;
  const deadline = params.get("deadline");
  const order = params.get("order") === "asc" ? "asc" : "desc";
  const filters: TaskFilters = {
    limit: 20,
    offset,
    sort_order: order,
    has_deadline:
      deadline === "true" ? true : deadline === "false" ? false : undefined,
  };
  const query = useQuery({
    queryKey: keys.taskList(filters),
    queryFn: ({ signal }) => listTasks(api, filters, signal),
  });
  function change(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (key !== "offset") next.delete("offset");
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }
  return (
    <div className="tasks-page flex flex-col gap-4">
      <div className="page-heading">
        <div>
          <h1>{t("المهام", "Tasks")}</h1>
          <p>
            {t(
              "مهام مستخرجة من بريدك. راجع الرسالة الأصلية للتأكد من التفاصيل.",
              "Tasks extracted from your email. Review the original for details.",
            )}
          </p>
        </div>
        {query.data && (
          <span className="count">
            {query.data.total} {t("مهمة", "tasks")}
          </span>
        )}
      </div>
      <RetroWindow
        title={t("المهام", "Tasks")}
        icon={<ListChecks size={16} className="text-[#E07A5F]" />}
      >
        <section className="surface border-0 rounded-none shadow-none">
          <div className="filters">
            <label>
              {t("الموعد النهائي", "Deadline")}
              <select
                value={
                  filters.has_deadline === undefined
                    ? ""
                    : String(filters.has_deadline)
                }
                onChange={(e) => change("deadline", e.target.value)}
              >
                <option value="">{t("الكل", "All")}</option>
                <option value="true">{t("بموعد نهائي", "Has deadline")}</option>
                <option value="false">
                  {t("بدون موعد نهائي", "No deadline")}
                </option>
              </select>
            </label>
            <label>
              {t("ترتيب الإضافة", "Order added")}
              <select
                value={order}
                onChange={(e) => change("order", e.target.value)}
              >
                <option value="desc">
                  {t("الأحدث إضافة", "Recently added")}
                </option>
                <option value="asc">{t("الأقدم إضافة", "Oldest added")}</option>
              </select>
            </label>
          </div>
          <div aria-live="polite" aria-busy={query.isFetching}>
            {query.isPending ? (
              <EmailSkeleton />
            ) : query.isError ? (
              <ErrorState
                error={query.error}
                retry={() => void query.refetch()}
              />
            ) : query.data.tasks.length ? (
              <ul className="task-results">
                {query.data.tasks.map((task) => (
                  <li key={task.id}>
                    <ContentText>{task.task}</ContentText>
                    <div className="task-deadline">
                      <strong>
                        {t("الموعد النهائي للمهمة", "Task deadline")}
                      </strong>
                      {task.deadline_text && (
                        <ContentText>{task.deadline_text}</ContentText>
                      )}
                      {task.deadline_at || task.deadline_date ? (
                        <EmailDate
                          value={task.deadline_at || task.deadline_date || ""}
                        />
                      ) : !task.deadline_text ? (
                        <span>
                          {t("لا يوجد موعد مستخرج", "No extracted deadline")}
                        </span>
                      ) : (
                        <small>
                          {t(
                            "لم يُحدّد تاريخ دقيق",
                            "No exact date determined",
                          )}
                        </small>
                      )}
                    </div>
                    <Link
                      className="task-source"
                      to={"/email/" + task.email.id}
                    >
                      <span>{t("المصدر:", "Source:")} </span>
                      <strong dir="auto">
                        {task.email.subject ||
                          t("بريد بلا عنوان", "Untitled email")}
                      </strong>
                      <span dir="auto">{task.email.sender}</span>
                      <small>
                        {t("تاريخ البريد: ", "Email date: ")}
                        <EmailDate
                          value={
                            task.email.sent_at ||
                            task.email.message_at ||
                            task.email.date ||
                            ""
                          }
                        />
                      </small>
                      <span className="source-action">
                        {t("فتح البريد", "Open email")}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <>
                <Empty
                  title={
                    filters.has_deadline !== undefined
                      ? t(
                          "لا توجد مهام تطابق الفلتر",
                          "No tasks match this filter",
                        )
                      : t("لا توجد مهام هنا", "No tasks here")
                  }
                  detail={t(
                    "تظهر هنا المهام المستخرجة من الرسائل المخزنة.",
                    "Extracted tasks from stored emails appear here.",
                  )}
                />
                <div className="center">
                  <button onClick={() => setParams({})}>
                    {t("عرض جميع المهام", "Show all tasks")}
                  </button>
                </div>
              </>
            )}
          </div>
          {query.data && !query.isError && (
            <div className="pagination">
              <button
                disabled={offset === 0 || query.isFetching}
                onClick={() =>
                  change("offset", String(Math.max(0, offset - 20)))
                }
              >
                {t("السابق", "Previous")}
              </button>
              <span>
                {query.data.count ? offset + 1 : 0}–
                {query.data.count ? offset + query.data.count : 0}{" "}
                {t("من", "of")} {query.data.total}
              </span>
              <button
                disabled={
                  query.isFetching ||
                  offset + query.data.limit >= query.data.total
                }
                onClick={() =>
                  change("offset", String(offset + query.data.limit))
                }
              >
                {t("التالي", "Next")}
              </button>
            </div>
          )}
        </section>
      </RetroWindow>
      <p className="feature-note muted">
        {t(
          "عرض للقراءة فقط؛ لا تتوفر حالة إنجاز للمهام.",
          "Read-only; task completion status is not available.",
        )}
      </p>
    </div>
  );
}
