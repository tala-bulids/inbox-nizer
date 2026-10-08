import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "../api/client";
import type { InboxFilters } from "../api/emails";
export const keys = {
  emails: ["emails"] as const,
  list: (filters: InboxFilters) => ["emails", "list", filters] as const,
  detail: (id: number) => ["emails", "detail", id] as const,
  search: (q: string) => ["search", q] as const,
  accounts: ["accounts"] as const,
};
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 300_000,
        refetchOnWindowFocus: false,
        retry: (n, error) =>
          n < 1 && error instanceof ApiError && error.code === "network",
      },
      mutations: { retry: false, gcTime: 0 },
    },
  });
}
