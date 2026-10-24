import { act, render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  GmailSyncProvider,
  useGmailSync,
} from "../features/settings/GmailSync";
import { ApiError } from "../api/client";
import { keys } from "../app/query";

const { api } = vi.hoisted(() => ({ api: { request: vi.fn() } }));
vi.mock("../auth/AuthProvider", () => ({ useAuth: () => ({ api }) }));
let lastSync: string | null;
let pending: boolean;
let status: string;
let calls: number;
let sourceFailed: number;
function Harness() {
  const { states, update } = useGmailSync();
  return (
    <>
      <button onClick={() => update(2)}>update</button>
      <output>{states[2]?.phase ?? "idle"}</output>
    </>
  );
}
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  client.setQueryData(keys.accounts, accountResponse());
  return render(
    <QueryClientProvider client={client}>
      <GmailSyncProvider>
        <Harness />
      </GmailSyncProvider>
    </QueryClientProvider>,
  );
}
function accountResponse() {
  return {
    sync_interval_seconds: 300,
    accounts: [
      {
        id: 2,
        address: "synthetic@example.invalid",
        status,
        last_synced_at: lastSync,
        sync_pending: pending,
        initial_sync_pending: !lastSync,
        message_count: 0,
        source_failed_count: sourceFailed,
      },
    ],
  };
}
beforeEach(() => {
  vi.useFakeTimers();
  lastSync = new Date().toISOString();
  pending = false;
  status = "connected";
  calls = 0;
  sourceFailed = 0;
  api.request.mockReset().mockImplementation(async (path: string) => {
    if (path.includes("/sync")) {
      calls++;
      lastSync = new Date().toISOString();
      pending = false;
      return {
        count: 1,
        success_count: 1,
        failed_count: 0,
        enrichment_failed: 0,
        has_more: false,
      };
    }
    return accountResponse();
  });
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});
const settle = async () => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
};

test("exhausted source failures stay stopped on reopen and allow an explicit retry", async () => {
  sourceFailed = 1;
  lastSync = null;
  const view = mount();
  await settle();
  expect(calls).toBe(0);
  view.unmount();
  mount();
  await settle();
  expect(calls).toBe(0);
  fireEvent.click(screen.getByText("update"));
  await settle();
  expect(calls).toBe(1);
  expect(
    api.request.mock.calls.some(([path]) => path.includes("retry_failed=true")),
  ).toBe(true);
});

test("fresh account auto starts and a resumed checkpoint also starts on reopen", async () => {
  lastSync = null;
  const view = mount();
  await settle();
  expect(calls).toBe(1);
  expect(screen.getByText("complete")).toBeVisible();
  view.unmount();
  pending = true;
  mount();
  await settle();
  expect(calls).toBe(2);
});

test("five consecutive failures stop automatic retries until a new session or manual update", async () => {
  lastSync = null;
  api.request.mockImplementation(async (path: string) => {
    if (!path.includes("/sync")) return accountResponse();
    calls++;
    throw new ApiError(503);
  });
  mount();
  await settle();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(4 * 60 * 60_000);
  });
  expect(calls).toBe(5);
  fireEvent.click(screen.getByText("update"));
  await settle();
  expect(calls).toBe(6);
});

test("recent sync is throttled; periodic and focus triggers do not overlap", async () => {
  mount();
  await settle();
  expect(calls).toBe(0);
  fireEvent.focus(window);
  fireEvent.focus(window);
  await settle();
  expect(calls).toBe(0);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(301_000);
  });
  expect(calls).toBe(1);
  fireEvent.focus(window);
  await settle();
  expect(calls).toBe(1);
});

test("focus after an idle interval catches new mail without waiting for the timer", async () => {
  mount();
  await settle();
  vi.setSystemTime(Date.now() + 301_000);
  fireEvent.focus(window);
  await settle();
  expect(calls).toBe(1);
});

test("revoked connection never auto-syncs and repeated manual clicks stay serialized", async () => {
  status = "reconnect_required";
  lastSync = null;
  const view = mount();
  await settle();
  expect(calls).toBe(0);
  view.unmount();
  status = "connected";
  lastSync = new Date().toISOString();
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  api.request.mockImplementation(async (path: string) => {
    if (!path.includes("/sync")) return accountResponse();
    calls++;
    await held;
    return {
      count: 0,
      success_count: 0,
      failed_count: 0,
      enrichment_failed: 0,
      has_more: false,
    };
  });
  mount();
  await settle();
  fireEvent.click(screen.getByText("update"));
  fireEvent.click(screen.getByText("update"));
  await settle();
  expect(calls).toBe(1);
  await act(async () => {
    release();
  });
});

test("temporary errors back off instead of creating a repeated auto-sync loop", async () => {
  lastSync = null;
  api.request.mockImplementation(async (path: string) => {
    if (!path.includes("/sync")) return accountResponse();
    calls++;
    throw new ApiError(429);
  });
  mount();
  await settle();
  expect(calls).toBe(1);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(60_000);
  });
  expect(calls).toBe(1);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(241_000);
  });
  expect(calls).toBe(2);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300_000);
  });
  expect(calls).toBe(2);
});

test("another tab holding the browser lock prevents a duplicate POST", async () => {
  const original = Object.getOwnPropertyDescriptor(navigator, "locks");
  const request = vi.fn(async (_name, _options, callback) => callback(null));
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request },
  });
  try {
    lastSync = null;
    mount();
    await settle();
    expect(request).toHaveBeenCalled();
    expect(calls).toBe(0);
  } finally {
    if (original) Object.defineProperty(navigator, "locks", original);
    else Reflect.deleteProperty(navigator, "locks");
  }
});
