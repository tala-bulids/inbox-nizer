import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthProvider";
import { z } from "zod";
import { parse } from "../../api/contracts";
import { useLocale } from "../../app/locale";
import { categoryLabel } from "../../app/categoryLabels";
import type { InboxFilters } from "../../api/emails";
export function InboxToolbar({
  filters,
  change,
}: {
  filters: InboxFilters;
  change: (key: string, value: string | string[]) => void;
}) {
  const { t, language } = useLocale();
  const [expanded, setExpanded] = useState(false);
  const picker = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!expanded) return;
    const close = (event: PointerEvent) => {
      if (!picker.current?.contains(event.target as Node)) setExpanded(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [expanded]);
  const { api } = useAuth();
  const options = useQuery({
    queryKey: ["email-categories"],
    queryFn: async ({ signal }) =>
      parse(
        z.array(z.string()),
        await api.request("/email-categories", { signal }),
      ),
    staleTime: Infinity,
  });
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
      <div
        className="category-picker"
        ref={picker}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget))
            setExpanded(false);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setExpanded(false);
            trigger.current?.focus();
          }
        }}
      >
        <span id="category-label">{t("التصنيف", "Category")}</span>
        <button
          type="button"
          ref={trigger}
          className="category-trigger"
          aria-labelledby="category-label category-selection"
          aria-expanded={expanded}
          aria-controls="category-options"
          disabled={!options.data?.length}
          onClick={() => setExpanded((value) => !value)}
        >
          <span id="category-selection">
            {options.isPending
              ? t("جارٍ التحميل…", "Loading…")
              : filters.categories?.length
                ? filters.categories
                    .map((category) => categoryLabel(category, language))
                    .join(t("، ", ", "))
                : t("كل التصنيفات", "All categories")}
          </span>
          <ChevronDown size={16} aria-hidden="true" />
        </button>
        {expanded && (
          <div
            id="category-options"
            className="category-options"
            role="group"
            aria-labelledby="category-label"
          >
            {(options.data || []).map((category) => (
              <label key={category} className="category-option">
                <input
                  type="checkbox"
                  checked={filters.categories?.includes(category) || false}
                  onChange={(event) => {
                    const selected = filters.categories || [];
                    change(
                      "category",
                      event.target.checked
                        ? [...selected, category]
                        : selected.filter((item) => item !== category),
                    );
                  }}
                />
                <span>{categoryLabel(category, language)}</span>
              </label>
            ))}
          </div>
        )}
      </div>
      {options.isError && (
        <small role="status">
          {t(
            "التصنيفات غير متاحة حاليًا.",
            "Categories are currently unavailable.",
          )}
        </small>
      )}
    </div>
  );
}
