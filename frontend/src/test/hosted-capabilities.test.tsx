import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { App } from "../app/App";
import { server, base } from "./server";
import { accountData } from "./fixtures";

test.each(["/search", "/ask"])(
  "Render hides navigation and blocks direct %s",
  async (path) => {
    server.use(
      http.get(base + "/gmail/accounts", () =>
        HttpResponse.json({ ...accountData, runtime_profile: "render-free" }),
      ),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>,
    );
    await user.type(
      await screen.findByLabelText("رمز الوصول التطويري"),
      "test-token",
    );
    await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
    await screen.findByRole("navigation");
    expect(
      screen.queryByRole("link", { name: "البحث" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "اسأل البريد" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText("سؤالك")).not.toBeInTheDocument();
    expect(
      screen.getByText("الصفحة غير موجودة", { selector: "h1" }),
    ).toBeVisible();
  },
);
