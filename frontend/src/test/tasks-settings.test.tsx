import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate, useLocation } from "react-router-dom";
import { http, HttpResponse, delay } from "msw";
import { App } from "../app/App";
import { server, base } from "./server";
import { taskPage, accountData, email } from "./fixtures";
function History() {
  const go = useNavigate();
  const loc = useLocation();
  return (
    <>
      <button onClick={() => go(-1)}>Back test</button>
      <span data-testid="url">{loc.pathname + loc.search}</span>
    </>
  );
}
async function open(path = "/tasks") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <History />
      <App />
    </MemoryRouter>,
  );
  await user.type(
    await screen.findByLabelText("رمز الوصول التطويري"),
    "synthetic-token",
  );
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  await screen.findByRole("navigation", { name: "التنقل الرئيسي" });
  return user;
}
const syncResult = {
  count: 2,
  success_count: 2,
  failed_count: 0,
  enrichment_failed: 0,
  emails: [{ body: "PRIVATE_BODY" }],
};

test("disconnect retains mail, disables sync and offers the existing reconnect flow", async () => {
  let disconnected = false;
  let calls = 0;
  server.use(
    http.get(base + "/gmail/accounts", () =>
      HttpResponse.json({
        ...accountData,
        accounts: [
          {
            ...accountData.accounts[0],
            status: disconnected ? "disconnected" : "connected",
          },
        ],
      }),
    ),
    http.delete(base + "/gmail/accounts/2/connection", async () => {
      calls++;
      await delay(100);
      disconnected = true;
      return HttpResponse.json({ status: "disconnected" });
    }),
    http.post(base + "/auth/google/start", () =>
      HttpResponse.json({
        authorization_url:
          "https://accounts.google.com/o/oauth2/auth?state=reconnect",
      }),
    ),
  );
  const user = await open("/settings");
  await user.click(
    await screen.findByRole("button", { name: "قطع اتصال Gmail" }),
  );
  expect(
    screen.getByRole("button", { name: "جاري قطع الاتصال…" }),
  ).toBeDisabled();
  expect(await screen.findByText("غير متصل")).toBeVisible();
  expect(screen.getByRole("button", { name: "تحديث الآن" })).toBeDisabled();
  expect(screen.getByText(/تبقى الرسائل المحفوظة/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "إعادة الاتصال" }));
  expect(
    await screen.findByRole("link", { name: "متابعة إلى Google" }),
  ).toHaveAttribute(
    "href",
    "https://accounts.google.com/o/oauth2/auth?state=reconnect",
  );
  expect(calls).toBe(1);
  await user.click(screen.getByRole("link", { name: "البريد الوارد" }));
  expect(await screen.findByText(email.subject)).toBeVisible();
});

test("failed disconnect keeps connected state and offers retry without automatic DELETE", async () => {
  let calls = 0;
  server.use(
    http.delete(base + "/gmail/accounts/2/connection", () => {
      calls++;
      return new HttpResponse(null, { status: 409 });
    }),
  );
  const user = await open("/settings");
  await user.click(
    await screen.findByRole("button", { name: "قطع اتصال Gmail" }),
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "قطع اتصال Gmail" }),
    ).toBeEnabled(),
  );
  expect(screen.getByText("متصل")).toBeVisible();
  expect(calls).toBe(1);
});

test("initial connection automatically syncs sequential batches and refreshes completion timestamp", async () => {
  let calls = 0;
  let active = 0;
  let maxActive = 0;
  server.use(
    http.get(base + "/gmail/accounts", () =>
      HttpResponse.json({
        accounts: [
          {
            ...accountData.accounts[0],
            sync_pending: calls < 3,
            last_synced_at: calls >= 3 ? "2026-10-23T10:30:00Z" : null,
          },
        ],
      }),
    ),
    http.post(base + "/gmail/accounts/2/sync", async () => {
      calls++;
      active++;
      maxActive = Math.max(maxActive, active);
      await delay(150);
      active--;
      return HttpResponse.json({
        ...syncResult,
        has_more: calls < 3,
        progress_token: `checkpoint-${calls}`,
      });
    }),
  );
  await open("/settings");
  expect(
    await screen.findByRole("button", { name: "جاري التحديث..." }),
  ).toBeDisabled();
  await screen.findByText(/تم تجهيز 2 رسالة/);
  await screen.findByText("تم تحديث البريد");
  expect(calls).toBe(3);
  expect(maxActive).toBe(1);
  expect(screen.getByRole("button", { name: "تحديث الآن" })).toBeEnabled();
  expect(screen.queryByText("متابعة المزامنة")).not.toBeInTheDocument();
  await waitFor(() =>
    expect(
      document.querySelector('time[datetime="2026-10-23T10:30:00Z"]'),
    ).not.toBeNull(),
  );
}, 15000);

test.each([409, 503, "network"])(
  "mid-run %s stops and one later click resumes saved work",
  async (status) => {
    let calls = 0;
    server.use(
      http.post(base + "/gmail/accounts/2/sync", () => {
        calls++;
        if (calls === 2)
          return status === "network"
            ? HttpResponse.error()
            : HttpResponse.json(
                { detail: "PRIVATE" },
                { status: Number(status) },
              );
        return HttpResponse.json({
          ...syncResult,
          has_more: calls === 1,
          progress_token: "saved",
        });
      }),
    );
    const user = await open("/settings");
    await user.click(await screen.findByRole("button", { name: "تحديث الآن" }));
    await screen.findByText(/لم يكتمل التحديث/);
    expect(calls).toBe(2);
    expect(document.body).not.toHaveTextContent("PRIVATE");
    await user.click(screen.getByRole("button", { name: "تحديث الآن" }));
    await screen.findByText(/تم تحديث البريد/);
    expect(calls).toBe(3);
  },
);

test.each(["partial", "stalled"])(
  "%s work pauses automatically without an infinite loop",
  async (reason) => {
    let calls = 0;
    server.use(
      http.post(base + "/gmail/accounts/2/sync", () => {
        calls++;
        return HttpResponse.json({
          ...syncResult,
          has_more: true,
          progress_token: "same",
          failed_count: reason === "partial" ? 1 : 0,
        });
      }),
    );
    const user = await open("/settings");
    await user.click(await screen.findByRole("button", { name: "تحديث الآن" }));
    await screen.findByText(/لم يكتمل التحديث/);
    expect(calls).toBe(reason === "partial" ? 1 : 2);
    expect(screen.getByRole("button", { name: "تحديث الآن" })).toBeEnabled();
  },
);

test("leaving Settings keeps syncing while the app remains usable", async () => {
  let calls = 0;
  let finishBatch!: () => void;
  const heldBatch = new Promise<void>((resolve) => {
    finishBatch = resolve;
  });
  server.use(
    http.post(base + "/gmail/accounts/2/sync", async () => {
      calls++;
      await heldBatch;
      return HttpResponse.json({
        ...syncResult,
        has_more: calls < 2,
        progress_token: String(calls),
      });
    }),
  );
  const user = await open("/settings");
  await user.click(await screen.findByRole("button", { name: "تحديث الآن" }));
  await waitFor(() => expect(calls).toBe(1));
  await user.click(screen.getByRole("link", { name: "المهام" }));
  await screen.findByText(taskPage.tasks[0]!.task);
  finishBatch();
  await delay(200);
  await waitFor(() => expect(calls).toBe(2));
});
test("task loading skeleton then mixed text/deadline/source metadata", async () => {
  server.use(
    http.get(base + "/tasks", async () => {
      await delay(300);
      return HttpResponse.json(taskPage);
    }),
  );
  await open();
  await screen.findByRole("status");
  expect(await screen.findByText(taskPage.tasks[0]!.task)).toHaveAttribute(
    "dir",
    "auto",
  );
  expect(document.querySelector('time[datetime="2026-10-12"]')).not.toBeNull();
  expect(screen.getByText("لا يوجد موعد مستخرج")).toBeVisible();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});
test.each([false, true])("tasks empty filtered=%s", async (filtered) => {
  server.use(
    http.get(base + "/tasks", () =>
      HttpResponse.json({ ...taskPage, count: 0, total: 0, tasks: [] }),
    ),
  );
  const user = await open(filtered ? "/?unused=1" : "/tasks");
  if (filtered) await user.click(screen.getByRole("link", { name: "المهام" }));
  if (filtered)
    await user.selectOptions(screen.getByLabelText("الموعد النهائي"), "true");
  expect(
    await screen.findByText(
      filtered ? "لا توجد مهام تطابق الفلتر" : "لا توجد مهام هنا",
    ),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "عرض جميع المهام" }));
  expect(screen.getByTestId("url")).toHaveTextContent("/tasks");
});
test("tasks pagination/filter and history restore real SQL query params", async () => {
  const requests: URLSearchParams[] = [];
  server.use(
    http.get(base + "/tasks", ({ request }) => {
      const p = new URL(request.url).searchParams;
      requests.push(p);
      return HttpResponse.json({
        ...taskPage,
        total: 45,
        offset: Number(p.get("offset")),
      });
    }),
  );
  const user = await open("/tasks?deadline=false&order=asc");
  await screen.findByText(taskPage.tasks[0]!.task);
  expect(screen.getByLabelText("الموعد النهائي")).toHaveValue("false");
  await user.click(screen.getByRole("button", { name: "التالي" }));
  await waitFor(() => expect(requests.at(-1)?.get("offset")).toBe("20"));
  expect(requests.at(-1)?.get("has_deadline")).toBe("false");
  await screen.findByText("21–22 من 45");
  await user.click(screen.getByRole("button", { name: "Back test" }));
  await screen.findByText("1–2 من 45");
  expect(screen.getByRole("button", { name: "الأقدم" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
test("task source opens email detail and back restores filter", async () => {
  const user = await open("/tasks?deadline=true&offset=20&order=asc");
  await user.click(
    await screen.findByRole("link", { name: /طلب مستندات Documents/ }),
  );
  await screen.findByText(email.body);
  await user.click(screen.getByRole("link", { name: "العودة إلى المهام" }));
  await screen.findByText(taskPage.tasks[0]!.task);
  expect(screen.getByLabelText("الموعد النهائي")).toHaveValue("true");
  expect(screen.getByTestId("url")).toHaveTextContent(
    "/tasks?deadline=true&offset=20&order=asc",
  );
  expect(screen.getByRole("button", { name: "الأقدم" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});
test.each(["network", "contract", 503])("tasks %s error safe", async (kind) => {
  server.use(
    http.get(base + "/tasks", () =>
      kind === "network"
        ? HttpResponse.error()
        : kind === "contract"
          ? HttpResponse.json({ tasks: 42 })
          : HttpResponse.json({ detail: "PRIVATE" }, { status: 503 }),
    ),
  );
  await open();
  expect(
    await screen.findByRole("alert", {}, { timeout: 4000 }),
  ).not.toHaveTextContent("PRIVATE");
});
test("task state is not inherited by another user", async () => {
  const user = await open();
  await screen.findByText(taskPage.tasks[0]!.task);
  await user.click(screen.getByRole("button", { name: "خروج" }));
  server.use(
    http.get(base + "/tasks", () =>
      HttpResponse.json({ ...taskPage, count: 0, total: 0, tasks: [] }),
    ),
  );
  await user.type(
    await screen.findByLabelText("رمز الوصول التطويري"),
    "other-token",
  );
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  await screen.findByText("لا توجد مهام هنا");
  expect(screen.queryByText(taskPage.tasks[0]!.task)).not.toBeInTheDocument();
});
test("settings connected and exact last sync without secrets", async () => {
  server.use(
    http.get(base + "/gmail/accounts", () =>
      HttpResponse.json({
        accounts: [
          {
            ...accountData.accounts[0],
            last_synced_at: "2026-10-08T12:00:00Z",
            access_token: "SECRET",
            sync_error: "INTERNAL",
          },
        ],
      }),
    ),
  );
  await open("/settings");
  await screen.findByText("متصل");
  expect(
    document.querySelector('time[datetime="2026-10-08T12:00:00Z"]'),
  ).not.toBeNull();
  expect(screen.queryByText("SECRET")).not.toBeInTheDocument();
  expect(screen.queryByText("INTERNAL")).not.toBeInTheDocument();
  expect(screen.getByText("جلسة تطوير محلية")).toBeVisible();
});
test.each(["disconnected", "reconnect_required"])(
  "settings %s cannot sync",
  async (status) => {
    server.use(
      http.get(base + "/gmail/accounts", () =>
        HttpResponse.json({
          accounts: [{ ...accountData.accounts[0], status }],
        }),
      ),
    );
    await open("/settings");
    expect(
      await screen.findByRole("button", { name: "تحديث الآن" }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "إعادة الاتصال" })).toBeEnabled();
  },
);
test("settings without accounts offers explicit connect", async () => {
  server.use(
    http.get(base + "/gmail/accounts", () =>
      HttpResponse.json({ accounts: [] }),
    ),
  );
  await open("/settings");
  expect(await screen.findByText("لا يوجد حساب متصل")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "اتصال Gmail أو إعادة الاتصال" }),
  ).toBeEnabled();
});
test("sync is explicit duplicate guarded with truthful pending/result", async () => {
  let calls = 0;
  server.use(
    http.post(base + "/gmail/accounts/2/sync", async () => {
      calls++;
      await delay(300);
      return HttpResponse.json(syncResult);
    }),
  );
  const user = await open("/settings");
  expect(calls).toBe(0);
  const button = await screen.findByRole("button", { name: "تحديث الآن" });
  await user.click(button);
  fireEvent.click(button);
  expect(
    screen.getByRole("button", { name: "جاري التحديث..." }),
  ).toBeDisabled();
  await screen.findByText(/تم تحديث البريد/);
  expect(calls).toBe(1);
  expect(screen.queryByText("PRIVATE_BODY")).not.toBeInTheDocument();
});
test.each([409, 503])(
  "sync %s normalized and no automatic retry",
  async (status) => {
    let calls = 0;
    server.use(
      http.post(base + "/gmail/accounts/2/sync", () => {
        calls++;
        return HttpResponse.json({ detail: "PRIVATE" }, { status });
      }),
    );
    const user = await open("/settings");
    await user.click(await screen.findByRole("button", { name: "تحديث الآن" }));
    expect(await screen.findByText(/لم يكتمل التحديث/)).not.toHaveTextContent(
      "PRIVATE",
    );
    expect(calls).toBe(1);
  },
);
test("successful sync invalidates tasks and account data", async () => {
  let taskCalls = 0,
    accountCalls = 0;
  server.use(
    http.get(base + "/tasks", () => {
      taskCalls++;
      return HttpResponse.json(taskPage);
    }),
    http.get(base + "/gmail/accounts", () => {
      accountCalls++;
      return HttpResponse.json(accountData);
    }),
    http.post(base + "/gmail/accounts/2/sync", () =>
      HttpResponse.json(syncResult),
    ),
  );
  const user = await open();
  await screen.findByText(taskPage.tasks[0]!.task);
  await user.click(screen.getByRole("link", { name: "الإعدادات" }));
  await user.click(await screen.findByRole("button", { name: "تحديث الآن" }));
  await screen.findByText(/تم تحديث البريد/);
  await user.click(screen.getByRole("link", { name: "المهام" }));
  await waitFor(() => expect(taskCalls).toBe(2));
  expect(accountCalls).toBeGreaterThan(1);
});
test("connect and reconnect use secure POST handshake and honest JSON-return guidance", async () => {
  server.use(
    http.get(base + "/gmail/accounts", () =>
      HttpResponse.json({
        accounts: [
          { ...accountData.accounts[0], status: "reconnect_required" },
        ],
      }),
    ),
  );
  let calls = 0;
  server.use(
    http.post(base + "/auth/google/start", () => {
      calls++;
      return HttpResponse.json({
        authorization_url:
          "https://accounts.google.com/o/oauth2/auth?state=synthetic",
      });
    }),
  );
  const user = await open("/settings");
  await user.click(screen.getByRole("button", { name: "إعادة الاتصال" }));
  const link = await screen.findByRole("link", { name: "متابعة إلى Google" });
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
  expect(screen.getByText(/نبدأ تجهيزه تلقائيًا/)).toBeVisible();
  expect(calls).toBe(1);
});
test.each([
  "https://accounts.google.com.evil.invalid/",
  "https://secret@accounts.google.com/",
  "https://accounts.google.com:444/",
  "http://accounts.google.com/",
])("reject unsafe OAuth URL %s", async (url) => {
  server.use(
    http.get(base + "/gmail/accounts", () =>
      HttpResponse.json({ accounts: [] }),
    ),
  );
  server.use(
    http.post(base + "/auth/google/start", () =>
      HttpResponse.json({ authorization_url: url }),
    ),
  );
  const user = await open("/settings");
  await user.click(
    screen.getByRole("button", { name: "اتصال Gmail أو إعادة الاتصال" }),
  );
  await screen.findByRole("alert");
  expect(
    screen.queryByRole("link", { name: "متابعة إلى Google" }),
  ).not.toBeInTheDocument();
});
test("401 from sync clears auth session", async () => {
  server.use(
    http.post(
      base + "/gmail/accounts/2/sync",
      () => new HttpResponse(null, { status: 401 }),
    ),
  );
  const user = await open("/settings");
  await user.click(await screen.findByRole("button", { name: "تحديث الآن" }));
  await screen.findByLabelText("رمز الوصول التطويري");
  expect(
    screen.queryByText(accountData.accounts[0]!.address),
  ).not.toBeInTheDocument();
});
