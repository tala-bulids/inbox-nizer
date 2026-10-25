import type { Email } from "../../api/contracts";
import { useLocale } from "../../app/locale";
import { ContentText } from "../../components/ui/Text";
import { EmailDate } from "../../components/ui/EmailDate";
export function EmailTasks({ tasks }: { tasks: Email["tasks"] }) {
  const { t } = useLocale();
  return (
    <section>
      <h3>{t("المهام والمواعيد المستخرجة", "Extracted tasks & deadlines")}</h3>
      {tasks.length ? (
        <ul className="task-list">
          {tasks.map((task, i) => (
            <li key={i}>
              <ContentText>{task.task}</ContentText>
              {(task.deadline_text ||
                task.deadline_date ||
                task.deadline_at) && (
                <div className="task-deadline">
                  <strong>{t("الموعد النهائي للمهمة", "Task deadline")}</strong>
                  {task.deadline_text && (
                    <ContentText>{task.deadline_text}</ContentText>
                  )}
                  {(task.deadline_at || task.deadline_date) && (
                    <EmailDate value={task.deadline_at || task.deadline_date} />
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">
          {t("لا توجد مهام مستخرجة", "No extracted tasks")}
        </p>
      )}
    </section>
  );
}
