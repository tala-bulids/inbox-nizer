import type { ApiClient } from "./client";
import { ApiError } from "./client";
import { accountsSchema, oauthSchema, syncSchema, parse } from "./contracts";
export const accounts = {
  list: async (api: ApiClient, signal?: AbortSignal) =>
    parse(accountsSchema, await api.request("/gmail/accounts", { signal })),
  sync: async (api: ApiClient, id: number, signal?: AbortSignal) =>
    parse(
      syncSchema,
      await api.request(`/gmail/accounts/${id}/sync`, {
        method: "POST",
        signal,
      }),
    ),
  signIn: async (api: ApiClient) =>
    googleRedirect(api, "/auth/google/login/start"),
  connect: async (api: ApiClient) =>
    googleRedirect(api, "/auth/google/start?browser=true"),
};

export type SyncProgress = {
  success_count: number;
  failed_count: number;
  enrichment_failed: number;
};
export type SyncRun = SyncProgress & {
  reason: "complete" | "partial" | "stalled" | "limit";
};

// One awaited request at a time. Never retry a POST whose outcome is unknown.
// PostgreSQL owns continuation; refreshing/closing the page leaves it resumable.
export async function syncAll(
  api: ApiClient,
  id: number,
  signal: AbortSignal,
  onProgress: (progress: SyncProgress) => void | Promise<void>,
): Promise<SyncRun> {
  const totals: SyncProgress = {
    success_count: 0,
    failed_count: 0,
    enrichment_failed: 0,
  };
  const seen = new Set<string>();
  const deadline = Date.now() + 30 * 60 * 1000;
  for (let batch = 0; batch < 1000 && Date.now() < deadline; batch++) {
    signal.throwIfAborted();
    const result = await accounts.sync(
      api,
      id,
      AbortSignal.any([signal, AbortSignal.timeout(90_000)]),
    );
    signal.throwIfAborted();
    totals.success_count += result.success_count;
    totals.failed_count += result.failed_count;
    totals.enrichment_failed += result.enrichment_failed;
    await onProgress({ ...totals });
    if (result.failed_count) return { ...totals, reason: "partial" };
    if (!result.has_more) return { ...totals, reason: "complete" };
    if (!result.progress_token || seen.has(result.progress_token))
      return { ...totals, reason: "stalled" };
    seen.add(result.progress_token);
  }
  return { ...totals, reason: "limit" };
}

async function googleRedirect(api: ApiClient, path: string) {
  const result = parse(
    oauthSchema,
    await api.request(path, { method: "POST" }),
  );
  const url = new URL(result.authorization_url);
  if (
    url.protocol !== "https:" ||
    url.hostname !== "accounts.google.com" ||
    url.username ||
    url.password ||
    url.port
  )
    throw new ApiError("contract");
  return url.href;
}
