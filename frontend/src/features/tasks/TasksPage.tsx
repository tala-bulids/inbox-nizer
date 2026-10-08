import { Link } from "react-router-dom";
import { useLocale } from "../../app/locale";
import { Empty } from "../../components/shared/States";
export function TasksPage() {
  const { t } = useLocale();
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">TASKS & DEADLINES</p>
          <h1>{t("المهام والمواعيد", "Tasks & deadlines")}</h1>
        </div>
      </div>
      <section className="surface">
        <Empty
          title={t(
            "قائمة المهام الموحّدة قيد التجهيز",
            "A unified task list is coming",
          )}
          detail={t(
            "الخلفية الحالية تعرض المهام داخل كل بريد، ولا توفر قائمة مهام مستقلة بعد.",
            "The backend currently exposes tasks within each email, not through a standalone task-list endpoint.",
          )}
        />
        <div className="center">
          <Link className="button" to="/?tasks=true">
            {t("عرض الرسائل التي تحتوي مهام", "Browse emails with tasks")}
          </Link>
        </div>
      </section>
    </>
  );
}
