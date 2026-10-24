import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { http, HttpResponse, delay } from "msw";
import { App } from "../app/App";
import { server, base } from "./server";
import { email, inbox } from "./fixtures";
import { readInboxState, inboxReturnPath } from "../features/inbox/inboxState";
import { formatEmailDate } from "../components/ui/EmailDate";
function History() {
  const loc = useLocation();
  const go = useNavigate();
  return (
    <>
      <output data-testid="location">{loc.pathname + loc.search}</output>
      <button onClick={() => go(-1)}>History back</button>
      <button onClick={() => go(1)}>History forward</button>
    </>
  );
}
async function open(path = "/") {
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

test("canonical category badges follow the selected language in Inbox and detail", async () => {
  const categorized = {
    ...email,
    predictions: [{ category: "Finance & Bills" }],
  };
  server.use(
    http.get(base + "/emails", () =>
      HttpResponse.json({ ...inbox, emails: [categorized] }),
    ),
    http.get(base + "/emails/11", () => HttpResponse.json(categorized)),
  );
  const user = await open();
  expect(await screen.findByText("مالية وفواتير")).toBeVisible();
  expect(screen.queryByText("Finance & Bills")).not.toBeInTheDocument();
  await user.click(screen.getByRole("heading", { name: email.subject }));
  await screen.findByRole("heading", { name: "نص البريد الأصلي المخزن" });
  expect(await screen.findByText("مالية وفواتير")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Switch to English" }));
  expect(screen.getByText("Finance & Bills")).toBeVisible();
  expect(screen.queryByText("مالية وفواتير")).not.toBeInTheDocument();
});

test("inbox preserves server message chronology despite reverse import dates", async () => {
  const items = [
    {
      ...email,
      id: 21,
      subject: "Newest sent",
      sent_at: "2026-10-12T00:00:00Z",
      created_at: "2026-10-01",
    },
    {
      ...email,
      id: 22,
      subject: "Older sent",
      sent_at: "2026-10-10T00:00:00Z",
      created_at: "2026-10-15",
    },
    {
      ...email,
      id: 23,
      subject: "Undated",
      date: "",
      created_at: "2026-10-20",
    },
  ];
  server.use(
    http.get(base + "/emails", () =>
      HttpResponse.json({ ...inbox, count: 3, total: 3, emails: items }),
    ),
  );
  await open();
  await screen.findByText("Undated");
  expect(
    screen.getAllByRole("heading", { level: 2 }).map((e) => e.textContent),
  ).toEqual(items.map((e) => e.subject));
  expect(readInboxState(new URLSearchParams("sort=created_at")).sort_by).toBe(
    "created_at",
  );
});
test("filtered empty clears filters and resets offset but preserves sort", async () => {
  server.use(
    http.get(base + "/emails", () =>
      HttpResponse.json({ ...inbox, total: 0, count: 0, emails: [] }),
    ),
  );
  const user = await open("/?priority=high&offset=20&sort=id");
  await screen.findByText("لا توجد رسائل تطابق الفلاتر");
  await user.click(screen.getAllByRole("button", { name: "مسح الفلاتر" })[0]!);
  expect(screen.getByTestId("location")).toHaveTextContent("/?sort=id");
  await screen.findByText("لا توجد رسائل هنا");
});
test("only priority and multi-select category controls remain and reset pagination", async () => {
  let last = new URLSearchParams();
  server.use(
    http.get(base + "/emails", ({ request }) => {
      last = new URL(request.url).searchParams;
      return HttpResponse.json({
        ...inbox,
        total: 81,
        offset: Number(last.get("offset")),
      });
    }),
  );
  const user = await open("/?offset=20");
  await screen.findByText(email.subject);
  await user.selectOptions(screen.getByLabelText("الأولوية"), "high");
  await waitFor(() => expect(last.get("priority_level")).toBe("high"));
  expect(last.get("offset")).toBe("0");
  await user.click(screen.getByRole("button", { name: /التصنيف/ }));
  await user.click(screen.getByRole("checkbox", { name: "طلبات التوظيف" }));
  await user.click(screen.getByRole("checkbox", { name: "شخصي" }));
  await waitFor(() =>
    expect(last.getAll("categories")).toEqual(["Job Application", "Personal"]),
  );
  const toolbar = screen
    .getByRole("button", { name: /التصنيف/ })
    .closest(".inbox-toolbar")!;
  expect(toolbar.querySelectorAll("select")).toHaveLength(1);
  expect(toolbar.querySelectorAll("button")).toHaveLength(1);
  expect(screen.getAllByRole("checkbox")).toHaveLength(10);
  await user.keyboard("{Escape}");
  expect(screen.getByRole("button", { name: /التصنيف/ })).toHaveFocus();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("الترتيب")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("الاتجاه")).not.toBeInTheDocument();
  expect(last.has("has_tasks")).toBe(false);
  expect(last.has("has_deadline")).toBe(false);
  expect(last.get("sort_by")).toBe("message_date");
  expect(last.get("limit")).toBe("20");
});
test("next previous and browser back forward restore URL and controls", async () => {
  server.use(
    http.get(base + "/emails", ({ request }) =>
      HttpResponse.json({
        ...inbox,
        total: 81,
        offset: Number(new URL(request.url).searchParams.get("offset")),
      }),
    ),
  );
  const user = await open("/?priority=high");
  await screen.findByText(email.subject);
  await user.click(screen.getByRole("button", { name: "التالي" }));
  await waitFor(() =>
    expect(screen.getByTestId("location")).toHaveTextContent("offset=20"),
  );
  await screen.findByText("21–21 من 81");
  await user.click(screen.getByRole("button", { name: "السابق" }));
  await screen.findByText("1–1 من 81");
  await user.click(screen.getByRole("button", { name: "History back" }));
  await screen.findByText("21–21 من 81");
  await user.click(screen.getByRole("button", { name: "History forward" }));
  await screen.findByText("1–1 من 81");
  expect(screen.getByLabelText("الأولوية")).toHaveValue("high");
});
test("keyboard row opens real detail URL and explicit back restores filters", async () => {
  const user = await open("/?tasks=true&category=Personal");
  const heading = await screen.findByRole("heading", { name: email.subject });
  const link = heading.closest("a")!;
  link.focus();
  await user.keyboard("{Enter}");
  await screen.findByText(email.body);
  expect(screen.getByTestId("location")).toHaveTextContent("/email/11");
  await user.click(
    screen.getByRole("link", { name: "العودة إلى البريد الوارد" }),
  );
  await screen.findByRole("heading", { name: email.subject });
  expect(screen.getByTestId("location")).toHaveTextContent(
    "/?tasks=true&category=Personal",
  );
  expect(screen.getByRole("button", { name: /التصنيف/ })).toHaveTextContent(
    "شخصي",
  );
});
test("detail skeleton retains back link", async () => {
  server.use(
    http.get(base + "/emails/:id", async () => {
      await delay(400);
      return HttpResponse.json(email);
    }),
  );
  await open("/email/11");
  expect(
    await screen.findByRole("status", { name: "جارٍ التحميل…" }),
  ).toHaveClass("detail-skeleton");
  expect(
    screen.getByRole("link", { name: "العودة إلى البريد الوارد" }),
  ).toBeVisible();
  await screen.findByText(email.body);
});
test.each([404, 500])("detail %s is safe and retryable", async (status) => {
  server.use(
    http.get(base + "/emails/:id", () =>
      HttpResponse.json({ detail: "PRIVATE" }, { status }),
    ),
  );
  await open("/email/11");
  const alert = await screen.findByRole("alert");
  expect(alert).not.toHaveTextContent("PRIVATE");
  expect(screen.getByRole("button", { name: "إعادة المحاولة" })).toBeVisible();
  if (status === 404) expect(alert).toHaveTextContent("غير متاح لحسابك");
});
test("missing optional fields degrade gracefully", async () => {
  server.use(
    http.get(base + "/emails/:id", () => HttpResponse.json({ id: 11 })),
  );
  await open("/email/11");
  expect(
    await screen.findByRole("heading", { name: "بلا عنوان" }),
  ).toBeVisible();
  expect(screen.getByText("مرسل غير معروف")).toBeVisible();
  expect(screen.getByText("لا يوجد ملخص")).toBeVisible();
  expect(screen.getByText("لا توجد مهام مستخرجة")).toBeVisible();
  expect(screen.getByText("لا يوجد محتوى نصي")).toBeVisible();
});
test("source summary task and deadline are separate, mixed body remains plain text", async () => {
  const body =
    'مرحبا mixed English <img src=x onerror="alert(1)"> reference ABC123';
  server.use(
    http.get(base + "/emails/:id", () =>
      HttpResponse.json({ ...email, body, sent_at: "2026-10-08T09:00:00Z" }),
    ),
  );
  await open("/email/11");
  expect(await screen.findByText(body)).toHaveAttribute("dir", "auto");
  expect(document.querySelector(".original img")).toBeNull();
  expect(screen.getByText(body).closest(".original")).not.toBeNull();
  expect(screen.getByText(email.summary).closest(".derived")).not.toBeNull();
  expect(screen.getByText(email.tasks[0]!.task)).toBeVisible();
  expect(screen.getByText("الموعد النهائي للمهمة")).toBeVisible();
  expect(document.querySelector('time[datetime="2026-10-12"]')).not.toBeNull();
  expect(
    document.querySelector('time[datetime="2026-10-08T09:00:00Z"]'),
  ).not.toBeNull();
});
test("many categories are bounded in inbox and body never displayed", async () => {
  server.use(
    http.get(base + "/emails", () =>
      HttpResponse.json({
        ...inbox,
        emails: [
          {
            ...email,
            predictions: ["A", "B", "C", "D"].map((category) => ({ category })),
          },
        ],
      }),
    ),
  );
  await open();
  await screen.findByText(email.subject);
  expect(screen.getByText("+2 تصنيفات")).toBeVisible();
  expect(screen.queryByText("C")).not.toBeInTheDocument();
  expect(screen.queryByText(email.body)).not.toBeInTheDocument();
});
test("normalized date formatter preserves calendar day and declines arbitrary headers", () => {
  expect(formatEmailDate("2026-10-12", "en")).toBe("12 Oct 2026");
  expect(formatEmailDate("2026-10-12", "ar")).toContain("٢٠٢٦");
  expect(formatEmailDate("not a date", "en")).toBeNull();
  expect(formatEmailDate("8 Oct 2026", "en")).toBeNull();
});
test("invalid URL state is bounded and return path cannot escape inbox", () => {
  expect(
    readInboxState(
      new URLSearchParams("offset=Infinity&priority=evil&sort=body&order=evil"),
    ),
  ).toMatchObject({
    offset: 0,
    sort_by: "message_date",
    sort_order: "desc",
    priority_level: undefined,
  });
  expect(inboxReturnPath("//evil.invalid")).toBe("/");
  expect(inboxReturnPath("/?tasks=true&token=secret")).toBe("/?tasks=true");
});

test("processing notice exposes no internal stage or error code", async () => {
  server.use(
    http.get(base + "/emails/:id", () =>
      HttpResponse.json({
        ...email,
        processing: [
          {
            status: "failed",
            stage: "INTERNAL_STAGE",
            error_code: "SECRET_CODE",
          },
        ],
      }),
    ),
  );
  await open("/email/11");
  await screen.findByText(email.body);
  expect(screen.getByText(/بعض المعلومات المساعدة/)).toBeVisible();
  expect(screen.queryByText("SECRET_CODE")).not.toBeInTheDocument();
  expect(screen.queryByText("INTERNAL_STAGE")).not.toBeInTheDocument();
});

test("legacy task filters do not silently constrain Inbox", async () => {
  let last = new URLSearchParams();
  server.use(
    http.get(base + "/emails", ({ request }) => {
      last = new URL(request.url).searchParams;
      return HttpResponse.json(inbox);
    }),
  );
  await open("/?tasks=false&deadline=true");
  await screen.findByText(email.subject);
  expect(last.has("has_tasks")).toBe(false);
  expect(last.has("has_deadline")).toBe(false);
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
});

test("category failure keeps the toolbar free of reload controls", async () => {
  server.use(
    http.get(
      base + "/email-categories",
      () => new HttpResponse(null, { status: 503 }),
    ),
  );
  await open();
  await screen.findByText("التصنيفات غير متاحة حاليًا.");
  expect(screen.getByRole("button", { name: /التصنيف/ })).toBeDisabled();
  expect(screen.getByLabelText("الأولوية")).toBeEnabled();
  expect(
    screen
      .getByRole("button", { name: /التصنيف/ })
      .closest(".inbox-toolbar")!
      .querySelectorAll("button"),
  ).toHaveLength(1);
});

test("category choices toggle independently and clicking outside closes the menu", async () => {
  const user = await open();
  const trigger = await screen.findByRole("button", { name: /التصنيف/ });
  await waitFor(() => expect(trigger).toBeEnabled());
  await user.click(trigger);
  await user.click(screen.getByRole("checkbox", { name: "سفر وحجوزات" }));
  await user.click(screen.getByRole("checkbox", { name: "شخصي" }));
  await user.click(screen.getByRole("checkbox", { name: "سفر وحجوزات" }));
  expect(screen.getByRole("checkbox", { name: "شخصي" })).toBeChecked();
  expect(
    screen.getByRole("checkbox", { name: "سفر وحجوزات" }),
  ).not.toBeChecked();
  await user.click(screen.getByLabelText("الأولوية"));
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  expect(trigger).toHaveTextContent("شخصي");
  await user.click(trigger);
  await user.click(screen.getByRole("checkbox", { name: "شخصي" }));
  expect(trigger).toHaveTextContent("كل التصنيفات");
});
