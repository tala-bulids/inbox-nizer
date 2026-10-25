import { ApiClient, ApiError } from "../api/client";
import { demoAccounts, demoEmails } from "./fixtures";

export class DemoClient extends ApiClient {
  constructor() {
    super(
      () => undefined,
      () => {},
    );
  }
  override async request(
    path: string,
    options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
  ): Promise<unknown> {
    options.signal?.throwIfAborted();
    if (
      (options.method || "GET") !== "GET" ||
      options.body !== undefined ||
      !path.startsWith("/") ||
      path.startsWith("//")
    )
      throw new ApiError(403);
    const url = new URL(path, "https://demo.invalid");
    if (url.origin !== "https://demo.invalid") throw new ApiError(403);
    const q = url.searchParams;
    const integer = (key: string, fallback: number, max: number) => {
      const value = q.has(key) ? Number(q.get(key)) : fallback;
      return Number.isSafeInteger(value) && value >= 0
        ? Math.min(value, max)
        : fallback;
    };
    const offset = integer("offset", 0, 10000);
    const limit = Math.max(1, integer("limit", 20, 100));
    const page = <T>(items: T[], key: string) => ({
      total: items.length,
      count: items.slice(offset, offset + limit).length,
      offset,
      limit,
      [key]: items.slice(offset, offset + limit),
    });
    let result: unknown;
    if (url.pathname === "/gmail/accounts") result = demoAccounts;
    else if (url.pathname === "/email-categories")
      result = [
        ...new Set(demoEmails.map((e) => e.predictions[0]?.category || "")),
      ].sort();
    else if (url.pathname === "/emails") {
      const categories = q.getAll("categories");
      const priority = q.get("priority_level");
      const order = q.get("sort_order") === "asc" ? 1 : -1;
      const rank: Record<string, number> = { high: 3, medium: 2, low: 1 };
      const sorted = demoEmails
        .filter(
          (e) =>
            (!categories.length ||
              categories.includes(e.predictions[0]?.category || "")) &&
            (!priority || priority === e.priority_level),
        )
        .sort((a, b) => {
          const by = q.get("sort_by");
          const value =
            by === "id"
              ? a.id - b.id
              : by === "priority_score"
                ? (rank[a.priority_level] || 0) - (rank[b.priority_level] || 0)
                : a.sent_at.localeCompare(b.sent_at);
          return order * (value || a.id - b.id);
        });
      result = page(sorted, "emails");
    } else if (/^\/emails\/\d+$/.test(url.pathname)) {
      result = demoEmails.find(
        (e) => e.id === Number(url.pathname.split("/").pop()),
      );
      if (!result) throw new ApiError(404);
    } else if (url.pathname === "/tasks") {
      const tasks = demoEmails
        .flatMap((e) =>
          e.tasks.map((task, i) => ({
            ...task,
            id: e.id * 100 + i,
            created_at: e.created_at,
            email: {
              id: e.id,
              subject: e.subject,
              sender: e.from,
              date: e.date,
              sent_at: e.sent_at,
              message_at: e.message_at,
            },
          })),
        )
        .filter(
          (t) =>
            !q.has("has_deadline") ||
            Boolean(t.deadline_date) === (q.get("has_deadline") === "true"),
        )
        .sort(
          (a, b) =>
            (q.get("sort_order") === "asc" ? 1 : -1) *
            (a.created_at.localeCompare(b.created_at) || a.id - b.id),
        );
      result = page(tasks, "tasks");
    } else throw new ApiError(403);
    // Callers cannot mutate the canonical fixtures or create real account state.
    return structuredClone(result);
  }
}
