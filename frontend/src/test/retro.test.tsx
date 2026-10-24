import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { App } from "../app/App";
import { RetroWindow } from "../components/ui/RetroWindow";
import { RetroInput } from "../components/ui/RetroInput";
import { SourceCard } from "../components/ui/SourceCard";
test("login has a single language control and translates without changing auth", async () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>,
  );
  expect(await screen.findByLabelText("رمز الوصول التطويري")).toHaveAttribute(
    "type",
    "password",
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Switch to English" }),
  );
  expect(screen.getByLabelText("Development access token")).toBeVisible();
  expect(
    screen.queryByLabelText("رمز الوصول التطويري"),
  ).not.toBeInTheDocument();
  expect(document.documentElement).toHaveAttribute("lang", "en");
  expect(document.documentElement).toHaveAttribute("dir", "ltr");
  expect(screen.queryByText("SMART INBOX")).not.toBeInTheDocument();
});
test("window chrome has no pretend controls; real callbacks are accessible", async () => {
  const close = vi.fn();
  const view = render(<RetroWindow title="Title">Content</RetroWindow>);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  view.rerender(
    <RetroWindow title="Title" onClose={close}>
      Content
    </RetroWindow>,
  );
  await userEvent.click(screen.getByRole("button", { name: "إغلاق النافذة" }));
  expect(close).toHaveBeenCalledOnce();
});
test("retro input connects its label and error for assistive technology", () => {
  render(<RetroInput label="Reference" error="Check the reference" />);
  const input = screen.getByLabelText("Reference");
  expect(input).toHaveAccessibleDescription("Check the reference");
  expect(input).toHaveAttribute("aria-invalid", "true");
});
test("source card links to detail without nested interactive elements", () => {
  render(
    <MemoryRouter>
      <SourceCard
        emailId={11}
        subject="Original source"
        excerpt="<script>text only</script>"
        language="en"
      />
    </MemoryRouter>,
  );
  const link = screen.getByRole("link", { name: "View Email" });
  expect(link).toHaveAttribute("href", "/email/11");
  expect(link.querySelector("button")).toBeNull();
  expect(screen.getByText(/<script>text only/)).toBeVisible();
});
