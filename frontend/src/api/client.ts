export class ApiError extends Error {
  constructor(public readonly code: number | "network" | "contract") {
    super("Request failed");
  }
}
export class ApiClient {
  private controller = new AbortController();
  constructor(
    private token: () => string | undefined,
    private unauthorized: () => void,
    private base = import.meta.env.VITE_API_BASE_URL || "/api",
  ) {}
  dispose() {
    this.controller.abort();
  }
  async request(
    path: string,
    options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
  ): Promise<unknown> {
    const headers: Record<string, string> = { Accept: "application/json" };
    const token = this.token();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (options.body !== undefined)
      headers["Content-Type"] = "application/json";
    const signal = options.signal
      ? AbortSignal.any([options.signal, this.controller.signal])
      : this.controller.signal;
    let response: Response;
    try {
      response = await fetch(this.base.replace(/\/$/, "") + path, {
        method: options.method || "GET",
        headers,
        body:
          options.body === undefined ? undefined : JSON.stringify(options.body),
        signal,
        credentials: "same-origin",
        cache: "no-store",
        redirect: "error",
      });
    } catch (error) {
      if (signal.aborted) throw error;
      throw new ApiError("network");
    }
    if (!response.ok) {
      if (response.status === 401) this.unauthorized();
      throw new ApiError(response.status);
    }
    try {
      return (await response.json()) as unknown;
    } catch {
      throw new ApiError("contract");
    }
  }
}
export function params(
  values: Record<string, string | number | boolean | null | undefined>,
) {
  return new URLSearchParams(
    Object.entries(values)
      .filter(([, v]) => v != null)
      .map(([k, v]) => [k, String(v)]),
  ).toString();
}
