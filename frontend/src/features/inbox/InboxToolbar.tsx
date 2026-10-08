import { useState } from "react";
import { useLocale } from "../../app/locale";
import type { InboxFilters } from "../../api/emails";
export function InboxToolbar({
  filters,
  change,
  clear,
}: {
  filters: InboxFilters;
  change: (key: string, value: string) => void;
  clear: () => void;
}) {
  const { t } = useLocale();
  const [category, setCategory] = useState(filters.category || "");
  return (
    <div className="filters inbox-toolbar">
      <label>
        {t("الأولوية", "Priority")}
        <select
          value={filters.priority_level || ""}
          onChange={(e) => change("priority", e.target.value)}
        >
          <option value="">{t("الكل", "All")}</option>
          <option value="high">{t("عالية", "High")}</option>
          <option value="medium">{t("متوسطة", "Medium")}</option>
          <option value="low">{t("منخفضة", "Low")}</option>
        </select>
      </label>
      <form
        className="category-filter"
        onSubmit={(e) => {
          e.preventDefault();
          change("category", category.trim());
        }}
      >
        <label>
          {t("التصنيف", "Category")}
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder={t("اسم التصنيف المطابق", "Exact category name")}
            dir="auto"
          />
        </label>
        <button type="submit">{t("تطبيق", "Apply")}</button>
      </form>
      <label>
        {t("الترتيب", "Sort")}
        <select
          value={filters.sort_by}
          onChange={(e) => change("sort", e.target.value)}
        >
          <option value="created_at">{t("تاريخ الإضافة", "Date added")}</option>
          <option value="priority_score">{t("الأولوية", "Priority")}</option>
          <option value="id">{t("معرّف الرسالة", "Email ID")}</option>
        </select>
      </label>
      <label>
        {t("الاتجاه", "Order")}
        <select
          value={filters.sort_order}
          onChange={(e) => change("order", e.target.value)}
        >
          <option value="desc">{t("تنازلي", "Descending")}</option>
          <option value="asc">{t("تصاعدي", "Ascending")}</option>
        </select>
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={filters.has_tasks === true}
          onChange={(e) => change("tasks", e.target.checked ? "true" : "")}
        />
        {t("بمهام", "Has tasks")}
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={filters.has_deadline === true}
          onChange={(e) => change("deadline", e.target.checked ? "true" : "")}
        />
        {t("بموعد نهائي", "Has deadline")}
      </label>
      {filters.has_tasks === false && (
        <button onClick={() => change("tasks", "")}>
          {t("بدون مهام ×", "Without tasks ×")}
        </button>
      )}
      {filters.has_deadline === false && (
        <button onClick={() => change("deadline", "")}>
          {t("بدون موعد نهائي ×", "Without deadline ×")}
        </button>
      )}
      <button onClick={clear}>{t("مسح الفلاتر", "Clear filters")}</button>
    </div>
  );
}
