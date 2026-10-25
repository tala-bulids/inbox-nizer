import type { operations } from "./generated/schema";
import type { ApiClient } from "./client";
import { params } from "./client";
import { emailSchema, inboxSchema, searchSchema, parse } from "./contracts";
export type InboxFilters = NonNullable<
  operations["get_saved_emails_emails_get"]["parameters"]["query"]
>;
export const emails = {
  retryEnrichment: (api: ApiClient, id: number) =>
    api.request(`/emails/${id}/retry-enrichment`, {
      method: "POST",
      signal: AbortSignal.timeout(90_000),
    }),
  list: async (api: ApiClient, filters: InboxFilters, signal?: AbortSignal) =>
    parse(
      inboxSchema,
      await api.request("/emails?" + params(filters), { signal }),
    ),
  detail: async (api: ApiClient, id: number, signal?: AbortSignal) =>
    parse(emailSchema, await api.request(`/emails/${id}`, { signal })),
  search: async (api: ApiClient, q: string, signal?: AbortSignal) =>
    parse(
      searchSchema,
      await api.request("/search/semantic?" + params({ q, limit: 10 }), {
        signal,
      }),
    ),
};
