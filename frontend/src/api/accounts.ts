import type { ApiClient } from "./client";
import { ApiError } from "./client";
import { accountsSchema, oauthSchema, syncSchema, parse } from "./contracts";
export const accounts = {
  list: async (api: ApiClient, signal?: AbortSignal) =>
    parse(accountsSchema, await api.request("/gmail/accounts", { signal })),
  sync: async (api: ApiClient, id: number) =>
    parse(
      syncSchema,
      await api.request(`/gmail/accounts/${id}/sync`, { method: "POST" }),
    ),
  signIn: async (api: ApiClient) =>
    googleRedirect(api, "/auth/google/login/start"),
  connect: async (api: ApiClient) =>
    googleRedirect(api, "/auth/google/start?browser=true"),
};
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
