import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { App } from "../app/App";
import { AppBoundary } from "../components/shared/AppBoundary";
import { server, base } from "./server";
import { accountData, inbox } from "./fixtures";
const csrf = "a".repeat(64);
function open(path = "/") {
  vi.stubEnv("VITE_AUTH_MODE", "browser");
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
function restore() {
  server.use(
    http.get(base + "/auth/session", () =>
      HttpResponse.json({ csrf_token: csrf }),
    ),
  );
}
test("browser login exchanges code once; cookie API uses CSRF and logout accepts 204", async () => {
  const calls: { path: string; auth: string | null; csrf: string | null }[] =
    [];
  server.use(
    http.get(
      base + "/auth/session",
      () => new HttpResponse(null, { status: 401 }),
    ),
    http.post(base + "/auth/session", ({ request }) => {
      calls.push({
        path: "login",
        auth: request.headers.get("authorization"),
        csrf: request.headers.get("x-csrf-token"),
      });
      return HttpResponse.json({ csrf_token: csrf });
    }),
    http.get(base + "/gmail/accounts", ({ request }) => {
      calls.push({
        path: "accounts",
        auth: request.headers.get("authorization"),
        csrf: request.headers.get("x-csrf-token"),
      });
      return HttpResponse.json(accountData);
    }),
    http.delete(base + "/auth/session", ({ request }) => {
      calls.push({
        path: "logout",
        auth: request.headers.get("authorization"),
        csrf: request.headers.get("x-csrf-token"),
      });
      return new HttpResponse(null, { status: 204 });
    }),
  );
  open();
  const user = userEvent.setup();
  await user.type(
    await screen.findByLabelText("رمز الدخول"),
    "temporary-admin-code",
  );
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  await screen.findByRole("navigation", { name: "التنقل الرئيسي" });
  await user.click(screen.getByRole("button", { name: "خروج" }));
  await screen.findByLabelText("رمز الدخول");
  await waitFor(() =>
    expect(calls).toContainEqual({ path: "logout", auth: null, csrf }),
  );
  expect(calls.filter((c) => c.path === "accounts")).toEqual([
    { path: "accounts", auth: null, csrf: null },
  ]);
  expect(calls[0]).toEqual({
    path: "login",
    auth: "Bearer temporary-admin-code",
    csrf: null,
  });
  expect(localStorage.length + sessionStorage.length).toBe(0);
});
test("existing browser session restores without an access code or duplicate account read", async () => {
  restore();
  let count = 0;
  server.use(
    http.get(base + "/gmail/accounts", () => {
      count++;
      return HttpResponse.json(accountData);
    }),
  );
  open();
  await screen.findByRole("navigation", { name: "التنقل الرئيسي" });
  expect(count).toBe(1);
  expect(screen.queryByLabelText("رمز الدخول")).not.toBeInTheDocument();
});
test("expired cookie clears private application state", async () => {
  restore();
  server.use(
    http.get(base + "/emails", () => new HttpResponse(null, { status: 401 })),
  );
  open();
  await screen.findByLabelText("رمز الدخول");
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
});
test("failed server logout clears UI and offers explicit revocation retry", async () => {
  restore();
  let attempts = 0;
  server.use(
    http.delete(base + "/auth/session", () =>
      ++attempts === 1
        ? new HttpResponse(null, { status: 503 })
        : new HttpResponse(null, { status: 204 }),
    ),
  );
  open();
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "خروج" }));
  const retry = await screen.findByRole("button", {
    name: "إعادة تسجيل الخروج",
  });
  expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  await user.click(retry);
  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: "إعادة تسجيل الخروج" }),
    ).not.toBeInTheDocument(),
  );
});
test("new login does not retain the previous user's inbox cache", async () => {
  restore();
  let second = false;
  server.use(
    http.get(base + "/emails", () =>
      HttpResponse.json({
        ...inbox,
        emails: inbox.emails.map((e) => ({
          ...e,
          subject: second ? "SECOND USER" : "FIRST USER",
        })),
      }),
    ),
    http.delete(base + "/auth/session", () => {
      second = true;
      return new HttpResponse(null, { status: 204 });
    }),
    http.post(base + "/auth/session", () =>
      HttpResponse.json({ csrf_token: csrf }),
    ),
  );
  open();
  const user = userEvent.setup();
  await screen.findAllByText("FIRST USER");
  await user.click(screen.getByRole("button", { name: "خروج" }));
  await waitFor(() =>
    expect(screen.getByLabelText("رمز الدخول")).toBeEnabled(),
  );
  await user.type(screen.getByLabelText("رمز الدخول"), "second-user-code");
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  await screen.findAllByText("SECOND USER");
  expect(screen.queryByText("FIRST USER")).not.toBeInTheDocument();
});
test.each([
  ["success", "انتهت خطوة اتصال Google"],
  ["denied", "لم تمنح الموافقة"],
  ["expired", "انتهت صلاحية محاولة الاتصال"],
  ["provider_error", "تعذر إكمال الاتصال"],
  ["SECRET_PROVIDER_DETAILS", "تعذر إكمال الاتصال"],
])("public OAuth completion is bounded and safe: %s", async (result, title) => {
  open("/oauth/complete?result=" + result);
  expect(await screen.findByRole("heading", { name: title })).toBeVisible();
  expect(
    screen.getByRole("link", { name: "الانتقال إلى الإعدادات" }),
  ).toHaveAttribute("href", "/settings");
  expect(screen.queryByText("SECRET_PROVIDER_DETAILS")).not.toBeInTheDocument();
});
test("unknown route has a useful localized 404", async () => {
  restore();
  open("/does-not-exist");
  expect(
    await screen.findByRole("heading", { name: "الصفحة غير موجودة" }),
  ).toBeVisible();
});
test("render failure shows recovery UI without error details", () => {
  const log = vi.spyOn(console, "error").mockImplementation(() => {});
  function Broken(): never {
    throw new Error("PRIVATE_EXCEPTION_BODY");
  }
  try {
    render(
      <AppBoundary>
        <Broken />
      </AppBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("تعذر عرض الصفحة");
    expect(
      screen.queryByText(/PRIVATE_EXCEPTION_BODY/),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "إعادة التحميل" })).toBeVisible();
  } finally {
    log.mockRestore();
  }
});
