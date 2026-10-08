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
    screen.getByLabelText("رمز الوصول التطويري"),
    "synthetic-token",
  );
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  await screen.findByRole("navigation", { name: "التنقل الرئيسي" });
  return user;
}
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
test("all filters and sorting use actual server parameters and reset pagination", async () => {
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
  await user.type(screen.getByLabelText("التصنيف"), "Job Application");
  await user.click(screen.getByRole("button", { name: "تطبيق" }));
  await waitFor(() => expect(last.get("category")).toBe("Job Application"));
  await user.click(screen.getByLabelText("بمهام"));
  await user.click(screen.getByLabelText("بموعد نهائي"));
  await user.selectOptions(screen.getByLabelText("الترتيب"), "priority_score");
  await user.selectOptions(screen.getByLabelText("الاتجاه"), "asc");
  await waitFor(() => expect(last.get("sort_order")).toBe("asc"));
  expect(last.get("has_tasks")).toBe("true");
  expect(last.get("has_deadline")).toBe("true");
  expect(last.get("sort_by")).toBe("priority_score");
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
  const user = await open("/?tasks=true&category=Events");
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
    "/?tasks=true&category=Events",
  );
  expect(screen.getByLabelText("التصنيف")).toHaveValue("Events");
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
    sort_by: "created_at",
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

test("negative boolean URL filters stay visible and removable", async () => {
  const user = await open("/?tasks=false&deadline=false");
  await screen.findByText(email.subject);
  expect(screen.getByRole("button", { name: "بدون مهام ×" })).toBeVisible();
  expect(
    screen.getByRole("button", { name: "بدون موعد نهائي ×" }),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "بدون مهام ×" }));
  expect(screen.getByTestId("location")).toHaveTextContent("/?deadline=false");
});
