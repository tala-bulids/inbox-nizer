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
    private csrf: () => string | undefined = () => undefined,
  ) {}
  dispose() {
    this.controller.abort();
  }
  async request(
    path: string,
    options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
  ): Promise<unknown> {
    // A static demo build must never contact even a same-origin mailbox API.
    if (import.meta.env.VITE_PUBLIC_DEMO === "true") throw new ApiError(403);
    const headers: Record<string, string> = { Accept: "application/json" };
    const token = this.token();
    if (token) headers.Authorization = `Bearer ${token}`;
    const csrf = this.csrf();
    if (
      !token &&
      csrf &&
      options.method &&
      !["GET", "HEAD", "OPTIONS"].includes(options.method)
    )
      headers["X-CSRF-Token"] = csrf;
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
    if (response.status === 204) return undefined;
    try {
      return (await response.json()) as unknown;
    } catch {
      throw new ApiError("contract");
    }
  }
}
export function params(
  values: Record<
    string,
    string | string[] | number | boolean | null | undefined
  >,
) {
  return new URLSearchParams(
    Object.entries(values)
      .filter(([, v]) => v != null)
      .flatMap(([k, v]) =>
        Array.isArray(v) ? v.map((item) => [k, item]) : [[k, String(v)]],
      ),
  ).toString();
}
