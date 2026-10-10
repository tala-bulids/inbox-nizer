import type { components, operations } from "./generated/schema";
import { ApiClient, ApiError, params } from "./client";
export type TaskPage = components["schemas"]["TaskPage"];
export type TaskItem = components["schemas"]["TaskItem"];
export type TaskFilters = NonNullable<
  operations["list_tasks_tasks_get"]["parameters"]["query"]
>;
export async function listTasks(
  api: ApiClient,
  filters: TaskFilters,
  signal?: AbortSignal,
): Promise<TaskPage> {
  const value = await api.request("/tasks?" + params(filters), { signal });
  if (
    !value ||
    typeof value !== "object" ||
    !("tasks" in value) ||
    !Array.isArray(value.tasks) ||
    !("total" in value) ||
    typeof value.total !== "number" ||
    !("count" in value) ||
    typeof value.count !== "number" ||
    !("limit" in value) ||
    typeof value.limit !== "number" ||
    !("offset" in value) ||
    typeof value.offset !== "number"
  )
    throw new ApiError("contract");
  for (const row of value.tasks) {
    if (
      !row ||
      !Number.isSafeInteger(row.id) ||
      row.id <= 0 ||
      typeof row.task !== "string" ||
      !row.email ||
      !Number.isSafeInteger(row.email.id) ||
      row.email.id <= 0
    )
      throw new ApiError("contract");
  }
  return value as TaskPage;
}
