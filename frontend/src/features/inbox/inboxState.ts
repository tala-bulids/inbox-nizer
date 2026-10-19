import type { InboxFilters } from "../../api/emails";
export function readInboxState(params: URLSearchParams): InboxFilters {
  const n = Number(params.get("offset") || 0);
  const priority = params.get("priority");
  const sort = params.get("sort");
  return {
    limit: 20,
    offset:
      Number.isSafeInteger(n) && n >= 0 && n <= Number.MAX_SAFE_INTEGER - 100
        ? n
        : 0,
    priority_level:
      priority === "high" || priority === "medium" || priority === "low"
        ? priority
        : undefined,
    categories: params.getAll("category").filter(Boolean),
    sort_by: sort === "priority_score" || sort === "id" ? sort : "created_at",
    sort_order: params.get("order") === "asc" ? "asc" : "desc",
  };
}
export function inboxReturnPath(value: unknown): string {
  if (typeof value !== "string" || !(value === "/" || value.startsWith("/?")))
    return "/";
  const params = new URLSearchParams(value.split("?")[1]);
  for (const key of [...params.keys()])
    if (
      ![
        "offset",
        "priority",
        "category",
        "tasks",
        "deadline",
        "sort",
        "order",
      ].includes(key)
    )
      params.delete(key);
  return params.size ? "/?" + params.toString() : "/";
}

export function emailReturnPath(value: unknown): string {
  if (value === "/search" || value === "/ask") return value;
  if (
    typeof value === "string" &&
    (value === "/tasks" || value.startsWith("/tasks?"))
  ) {
    const params = new URLSearchParams(value.split("?")[1]);
    for (const key of [...params.keys()])
      if (!["offset", "deadline", "order"].includes(key)) params.delete(key);
    return "/tasks" + (params.size ? "?" + params.toString() : "");
  }
  return inboxReturnPath(value);
}
