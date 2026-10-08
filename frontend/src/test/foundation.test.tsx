import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse, delay } from "msw";
import { App } from "../app/App";
import { ApiClient, ApiError } from "../api/client";
import { server, base } from "./server";
import {
  email,
  inbox,
  generated,
  clarification,
  supported,
  accountData,
} from "./fixtures";

async function open(path = "/") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  await user.type(
    screen.getByLabelText("رمز الوصول التطويري"),
    "test-session-token",
  );
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  await screen.findByRole("navigation", { name: "التنقل الرئيسي" });
  return user;
}
async function question() {
  const user = await open("/ask");
  await user.type(
    screen.getByLabelText("سؤالك"),
    "What happened with my application?",
  );
  await user.click(screen.getByRole("button", { name: "اسأل البريد" }));
  return user;
}

test("app renders memory-only development login", () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "مساحة أهدأ",
  );
  expect(screen.getByLabelText("رمز الوصول التطويري")).toHaveAttribute(
    "type",
    "password",
  );
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});
test("RTL shell and English identifier isolation", async () => {
  await open();
  await screen.findByText(email.subject);
  expect(document.documentElement).toHaveAttribute("dir", "rtl");
  expect(document.documentElement).toHaveAttribute("lang", "ar");
  expect(screen.getAllByText(email.date)[0]?.closest("bdi")).toHaveAttribute(
    "dir",
    "ltr",
  );
});
test("navigation switches routes and LTR", async () => {
  const user = await open();
  await user.click(screen.getByRole("link", { name: "البحث" }));
  expect(
    await screen.findByRole("heading", { name: "ابحث بالمعنى" }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Switch to English" }));
  expect(document.documentElement).toHaveAttribute("dir", "ltr");
  expect(
    screen.getByRole("heading", { name: "Search by meaning" }),
  ).toBeVisible();
});
test("auth header used without logging or persistence", async () => {
  let auth = "";
  server.use(
    http.get(base + "/gmail/accounts", ({ request }) => {
      auth = request.headers.get("Authorization") || "";
      return HttpResponse.json(accountData);
    }),
  );
  await open();
  expect(auth).toBe("Bearer test-session-token");
  expect(
    screen.queryByDisplayValue("test-session-token"),
  ).not.toBeInTheDocument();
  expect(localStorage.length + sessionStorage.length).toBe(0);
});
test("401 clears session and hides previously cached mailbox", async () => {
  const user = await open();
  await screen.findByText(email.subject);
  server.use(
    http.get(
      base + "/gmail/accounts",
      () => new HttpResponse(null, { status: 401 }),
    ),
  );
  await user.click(screen.getByRole("link", { name: "الإعدادات" }));
  await user.click(await screen.findByRole("button", { name: "تحديث الحالة" }));
  await screen.findByLabelText("رمز الوصول التطويري");
  expect(screen.queryByText(email.subject)).not.toBeInTheDocument();
});
test.each([403, 404, 409, 422, 503, 500])(
  "normalizes HTTP %s without raw details",
  async (status) => {
    server.use(
      http.get(base + "/emails", () =>
        HttpResponse.json({ detail: "PRIVATE_STACK_TRACE" }, { status }),
      ),
    );
    await open();
    expect(await screen.findByRole("alert")).not.toHaveTextContent(
      "PRIVATE_STACK_TRACE",
    );
  },
);
test("network errors are normalized", async () => {
  server.use(http.get(base + "/broken", () => HttpResponse.error()));
  await expect(
    new ApiClient(
      () => undefined,
      () => {},
      base,
    ).request("/broken"),
  ).rejects.toMatchObject({ code: "network" });
});
test("inbox loading", async () => {
  server.use(
    http.get(base + "/emails", async () => {
      await delay(300);
      return HttpResponse.json(inbox);
    }),
  );
  await open();
  expect(await screen.findByRole("status")).toHaveTextContent("جارٍ التحميل");
  await screen.findByText(email.subject);
});
test("inbox success includes source preview and pagination", async () => {
  await open();
  expect(
    await screen.findByRole("heading", { name: email.subject }),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "التالي" })).toBeDisabled();
});
test("inbox empty", async () => {
  server.use(
    http.get(base + "/emails", () =>
      HttpResponse.json({ ...inbox, total: 0, count: 0, emails: [] }),
    ),
  );
  await open();
  expect(await screen.findByText("لا توجد رسائل هنا")).toBeVisible();
});
test("detail route shows original safely separate from AI", async () => {
  await open("/email/11");
  expect(await screen.findByText(email.body)).toBeVisible();
  expect(screen.getByText("نص البريد الأصلي المخزن")).toBeVisible();
  expect(screen.getByText("ملخص آلي")).toBeVisible();
  expect(document.querySelector("script")).toBeNull();
  expect(screen.getByText(email.body)).toHaveAttribute("dir", "auto");
});
test("source supported state never labels independently verified truth", async () => {
  await question();
  expect(await screen.findByText("مدعوم من البريد")).toBeVisible();
  expect(screen.getByText("ليس تحققًا مستقلًا من الحقيقة")).toBeVisible();
});
test("generated synthesis warning stays visible and backend notice preserved", async () => {
  server.use(http.post(base + "/ask", () => HttpResponse.json(generated)));
  await question();
  expect(await screen.findByRole("note")).toHaveTextContent(
    "قد يُسقط النص شروطًا",
  );
  expect(
    screen.getByText(
      /Generated synthesis, not a semantically verified extraction/,
    ).textContent,
  ).toBe(generated.answer);
  expect(screen.queryByText("مدعوم من البريد")).not.toBeInTheDocument();
});
test("clarification follows up with ORIGINAL question and selected email_id", async () => {
  let body: unknown;
  let calls = 0;
  server.use(
    http.post(base + "/ask", async ({ request }) => {
      body = await request.json();
      return HttpResponse.json(++calls === 1 ? clarification : supported);
    }),
  );
  const user = await question();
  await screen.findByText("حدد الطلب المقصود");
  await user.clear(screen.getByLabelText("سؤالك"));
  await user.type(screen.getByLabelText("سؤالك"), "different draft");
  await user.click(screen.getByRole("button", { name: /طلب الجهة الأولى/ }));
  await screen.findByText("مدعوم من البريد");
  expect(body).toEqual({
    question: "What happened with my application?",
    email_id: 11,
  });
});
test("insufficient evidence is calm, not an operational error", async () => {
  server.use(
    http.post(base + "/ask", () =>
      HttpResponse.json({
        status: "insufficient_evidence",
        answer: "No evidence",
        sources: [],
        citations: [],
      }),
    ),
  );
  await question();
  expect(await screen.findByText("لا توجد أدلة كافية")).toBeVisible();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
test("provider error distinct from no evidence", async () => {
  server.use(
    http.post(base + "/ask", () => new HttpResponse(null, { status: 503 })),
  );
  await question();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "الخدمة غير متاحة",
  );
});
test("source links open email detail", async () => {
  const user = await question();
  await screen.findByText("مدعوم من البريد");
  await user.click(
    screen.getByRole("link", { name: new RegExp(email.subject) }),
  );
  expect(await screen.findByText("نص البريد الأصلي المخزن")).toBeVisible();
});
test.each([
  { ...supported, verification: undefined, answer_mode: undefined },
  { ...generated, verification: "source_supported" as const },
])(
  "missing or conflicting verification never implies verified",
  async (answer) => {
    server.use(http.post(base + "/ask", () => HttpResponse.json(answer)));
    await question();
    expect(await screen.findByRole("note")).toBeVisible();
    expect(screen.queryByText("مدعوم من البريد")).not.toBeInTheDocument();
  },
);
test("logout clears content; next user cannot see old cache", async () => {
  const user = await open();
  await screen.findByText(email.subject);
  await user.click(screen.getByRole("button", { name: "خروج" }));
  server.use(
    http.get(base + "/emails", () =>
      HttpResponse.json({ ...inbox, emails: [], count: 0, total: 0 }),
    ),
  );
  await user.type(screen.getByLabelText("رمز الوصول التطويري"), "other-token");
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  await screen.findByText("لا توجد رسائل هنا");
  expect(screen.queryByText(email.subject)).not.toBeInTheDocument();
});
test("tasks shell reports API gap and links to real filter", async () => {
  await open("/tasks");
  expect(
    await screen.findByText("قائمة المهام الموحّدة قيد التجهيز"),
  ).toBeVisible();
  expect(
    screen.getByRole("link", { name: "عرض الرسائل التي تحتوي مهام" }),
  ).toHaveAttribute("href", "/?tasks=true");
});
test("search submits only explicitly and opens discovery result", async () => {
  const user = await open("/search");
  await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "travel");
  expect(screen.queryByText(email.subject)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "بحث" }));
  expect(await screen.findByText("Original matched source text")).toBeVisible();
});
test("pagination sends SQL API offset and preserves filters", async () => {
  const offsets: string[] = [];
  server.use(
    http.get(base + "/emails", ({ request }) => {
      offsets.push(new URL(request.url).searchParams.get("offset") || "");
      return HttpResponse.json({ ...inbox, total: 41 });
    }),
  );
  const user = await open("/?tasks=true");
  await screen.findByText(email.subject);
  await user.click(screen.getByRole("button", { name: "التالي" }));
  await waitFor(() => expect(offsets).toEqual(["0", "20"]));
  expect(screen.getByRole("checkbox", { name: "بمهام" })).toBeChecked();
});
test("malformed responses produce safe contract errors", async () => {
  server.use(
    http.get(base + "/emails", () => HttpResponse.json({ private: "broken" })),
  );
  await open();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "وصل رد غير متوقع",
  );
  expect(new ApiError("contract").message).not.toContain("private");
});

test("settings sync is explicit and does not display returned bodies", async () => {
  let calls = 0;
  server.use(
    http.post(base + "/gmail/accounts/2/sync", () => {
      calls++;
      return HttpResponse.json({
        count: 1,
        success_count: 1,
        failed_count: 0,
        enrichment_failed: 0,
        emails: [{ body: "PRIVATE_SYNC_BODY" }],
      });
    }),
  );
  const user = await open("/settings");
  expect(calls).toBe(0);
  await user.click(await screen.findByRole("button", { name: "مزامنة الآن" }));
  expect(await screen.findByRole("status")).toHaveTextContent("تمت معالجة");
  expect(calls).toBe(1);
  expect(screen.queryByText("PRIVATE_SYNC_BODY")).not.toBeInTheDocument();
});

test("OAuth start refuses an arbitrary redirect host", async () => {
  server.use(
    http.post(base + "/auth/google/start", () =>
      HttpResponse.json({
        authorization_url: "https://attacker.invalid/steal",
      }),
    ),
  );
  const user = await open("/settings");
  await user.click(
    await screen.findByRole("button", { name: "اتصال Gmail أو إعادة الاتصال" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "وصل رد غير متوقع",
  );
  expect(
    screen.queryByRole("link", { name: "متابعة إلى Google" }),
  ).not.toBeInTheDocument();
});
