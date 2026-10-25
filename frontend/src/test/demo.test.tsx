import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { DemoApp } from "../demo/DemoApp";
import { DemoClient } from "../demo/DemoClient";
import { demoEmails } from "../demo/fixtures";
import { emails } from "../api/emails";
import { ApiClient } from "../api/client";
import { App } from "../app/App";

async function open(path = "/") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <DemoApp />
    </MemoryRouter>,
  );
  await user.click(screen.getByRole("button", { name: "Switch to English" }));
  return user;
}
afterEach(() => vi.restoreAllMocks());
test("public demo uses no fetch, cookies, session storage or login; real controls work", async () => {
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  const cookie = vi.spyOn(Document.prototype, "cookie", "get");
  const storage = vi.spyOn(Storage.prototype, "getItem");
  const user = await open();
  expect(await screen.findByText("24 messages")).toBeVisible();
  expect(screen.getByText("Interactive Demo — Sample Data")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Continue with Google" }),
  ).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Priority"), "high");
  expect(await screen.findByText("5 messages")).toBeVisible();
  await user.click(
    screen.getByRole("button", { name: /Category All categories/ }),
  );
  await user.click(screen.getByRole("checkbox", { name: "Job Application" }));
  expect(await screen.findByText("2 messages")).toBeVisible();
  await user.click(
    screen.getByRole("link", { name: /Interview invitation — Cedar Studio/ }),
  );
  expect(
    await screen.findByRole("heading", { name: "Example summary" }),
  ).toBeVisible();
  expect(screen.getByText(demoEmails[0]!.body)).toBeVisible();
  expect(fetchSpy).not.toHaveBeenCalled();
  expect(cookie).not.toHaveBeenCalled();
  expect(storage).not.toHaveBeenCalled();
}, 15000);
test("pagination, source tasks and language switch stay inside sample data", async () => {
  const user = await open();
  await screen.findByText("24 messages");
  await user.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("Next milestone — prototype review");
  expect(
    screen.queryByText("Interview invitation — Cedar Studio"),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Tasks" }));
  await screen.findByText("Confirm interview availability");
  await user.click(
    screen.getByRole("link", { name: /Source: Interview invitation/ }),
  );
  await screen.findByRole("heading", {
    name: "Interview invitation — Cedar Studio",
  });
  await user.click(screen.getByRole("button", { name: "التبديل للعربية" }));
  await waitFor(() => expect(document.documentElement.dir).toBe("rtl"));
  expect(screen.getByRole("heading", { name: "ملخص تجريبي" })).toBeVisible();
});
test("direct detail, settings and unsupported private paths cannot open accounts", async () => {
  const user = await open("/email/2");
  await screen.findByRole("heading", { name: "مراجعة خطة المشروع" });
  await user.click(screen.getByRole("link", { name: "Settings" }));
  expect(
    await screen.findByRole("heading", { name: "Gmail is not connected" }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Connect Gmail unavailable in demo" }),
  ).toBeDisabled();
  expect(
    screen.queryByRole("link", { name: "Search" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Sign out" }),
  ).not.toBeInTheDocument();
});
test.each([
  "/api/gmail/accounts",
  "/auth/session",
  "/search",
  "/ask",
  "/oauth/complete",
])("demo route %s has no private route fallback", async (path) => {
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  await open(path);
  expect(screen.getByRole("heading", { name: "Page not found" })).toBeVisible();
  expect(fetchSpy).not.toHaveBeenCalled();
});
test("demo client denies mutations, arbitrary IDs, auth and external origins without network", async () => {
  const spy = vi.spyOn(globalThis, "fetch");
  const api = new DemoClient();
  for (const path of [
    "/auth/session",
    "/auth/google/start",
    "/gmail/accounts/1/sync",
    "https://inbox-nizer-beta.onrender.com/api/emails",
    "//other.invalid/emails",
  ])
    await expect(api.request(path)).rejects.toMatchObject({ code: 403 });
  await expect(
    api.request("/emails", { method: "POST", body: {} }),
  ).rejects.toMatchObject({ code: 403 });
  await expect(emails.detail(api, 999999)).rejects.toMatchObject({ code: 404 });
  const page = await emails.list(api, { limit: 20, offset: 20 });
  expect(page.emails).toHaveLength(4);
  page.emails[0]!.body = "mutated";
  expect((await emails.detail(api, page.emails[0]!.id)).body).not.toBe(
    "mutated",
  );
  expect(demoEmails.every((e) => e.from.endsWith("@example.invalid"))).toBe(
    true,
  );
  expect(spy).not.toHaveBeenCalled();
});
test("static build network guard denies accidental real ApiClient before accessing credentials", async () => {
  vi.stubEnv("VITE_PUBLIC_DEMO", "true");
  const credentials = vi.fn();
  const spy = vi.spyOn(globalThis, "fetch");
  await expect(
    new ApiClient(credentials, vi.fn()).request("/auth/session"),
  ).rejects.toMatchObject({ code: 403 });
  expect(credentials).not.toHaveBeenCalled();
  expect(spy).not.toHaveBeenCalled();
});
test("the private app still requires authentication for direct email routes", async () => {
  render(
    <MemoryRouter initialEntries={["/email/1"]}>
      <App />
    </MemoryRouter>,
  );
  expect(
    await screen.findByRole("button", { name: "المتابعة باستخدام Google" }),
  ).toBeVisible();
  expect(
    screen.queryByText("Interactive Demo — Sample Data"),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText("Interview invitation — Cedar Studio"),
  ).not.toBeInTheDocument();
});
