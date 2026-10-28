import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ShowcaseApp } from "../showcase/ShowcaseApp";

const email = {
  id: 1,
  subject: "Atlas workshop",
  body: "Workshop date: 2026-11-05\nPlease submit the form by 2026-11-02.",
  date: "2026-10-20T09:00:00+00:00",
  language: "en",
  sender: "learning@example.invalid",
};
let calls: { url: string; init: RequestInit | undefined }[];
beforeEach(() => {
  calls = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push({ url: String(url), init });
    const path = String(url);
    if (path.endsWith("collection"))
      return Response.json({
        provenance: "Authored fictional collection",
        emails: [email],
      });
    if (path.endsWith("ask"))
      return Response.json({
        status: "answered",
        answer: "Workshop date: 2026-11-05 [email_id=1]",
        mode: "literal_fact",
        verification: "source_supported",
        sources: [
          {
            email_id: 1,
            subject: email.subject,
            content: email.body,
            score: 0.8,
          },
        ],
      });
    if (path.endsWith("analyze"))
      return Response.json({
        predictions: [{ category: "Events & Invitations", confidence: 0.6 }],
        summary: "Please submit the form.",
        classifier_status: "experimental",
        summary_method: "extractive",
      });
    if (path.endsWith("tasks"))
      return Response.json({
        method: "rules",
        tasks: [
          {
            email_id: 1,
            task: "Submit the form",
            confidence: 0.9,
            deadline_text: "2026-11-02",
            deadline_date: "2026-11-02",
            responsible: "Maya",
            deadline_state: "explicit",
            state: "open",
            evidence: { subject: email.subject, body: email.body },
          },
        ],
      });
    if (path.endsWith("lab"))
      return Response.json({
        checkpoint: "checkpoint-3159",
        weight_sha256: "97a26b67",
        provenance: "PASS",
        quality: "FAIL",
        evidence_date: "2026-10-24",
        methodology: "Original training split/report unavailable",
        inference: "ONNX",
        development: { n: 100, top1_accuracy: 0.32, top1_macro_f1: 0.2839 },
        languages: {
          English: { n: 56, correct: 20 },
          "Arabic-heavy": { n: 11, correct: 1 },
        },
      });
    throw new Error("Unexpected route");
  });
});

test("public Ask is extractive and tasks link to supporting original mail", async () => {
  const user = await open("/tasks");
  await user.click(screen.getByRole("button", { name: "Extract tasks" }));
  expect(await screen.findByText("Responsible: Maya")).toBeVisible();
  expect(screen.getByText("Deadline state: Explicit")).toBeVisible();
  await user.click(screen.getByRole("link", { name: "Open supporting email" }));
  expect(screen.getByText(/not LLM generation/)).toBeVisible();
  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Choose a source")).toHaveValue("1");
});
afterEach(() => vi.restoreAllMocks());
async function open(path = "/") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <ShowcaseApp />
    </MemoryRouter>,
  );
  await user.click(screen.getByRole("button", { name: "Switch to English" }));
  await screen.findByLabelText("Choose a source");
  return user;
}
test("anonymous Ask sends no credentials and renders computed answer with source", async () => {
  const user = await open();
  expect(screen.queryByText("Continue with Google")).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "What is the Atlas workshop date?" }),
  );
  await user.click(screen.getByRole("button", { name: "Ask AI" }));
  expect(
    await screen.findByText("Workshop date: 2026-11-05 [email_id=1]"),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: /Open source/ })).toHaveAttribute(
    "href",
    "/?email=1",
  );
  expect(
    calls.every(
      (c) =>
        c.url.startsWith("/api/showcase/") && c.init?.credentials === "omit",
    ),
  ).toBe(true);
  expect(
    JSON.parse(String(calls.find((c) => c.url.endsWith("ask"))?.init?.body)),
  ).toEqual({ question: "What is the Atlas workshop date?", mode: "grounded" });
});
test("live prediction is explicit and editable; tasks include original evidence", async () => {
  const user = await open("/intelligence");
  expect(calls.some((c) => c.url.endsWith("analyze"))).toBe(false);
  await user.clear(screen.getByLabelText("Text"));
  await user.type(
    screen.getByLabelText("Text"),
    "Please review this fictional report.",
  );
  await user.click(screen.getByRole("button", { name: "Run prediction" }));
  expect(await screen.findByText(/Events & Invitations/)).toBeVisible();
  expect(
    JSON.parse(String(calls.find((c) => c.url.endsWith("analyze"))?.init?.body))
      .body,
  ).toBe("Please review this fictional report.");
  await user.click(screen.getByRole("link", { name: "Smart Tasks" }));
  await user.click(screen.getByRole("button", { name: "Extract tasks" }));
  expect(await screen.findByText("Submit the form")).toBeVisible();
  await user.click(screen.getByText("Original source"));
  expect(
    screen.getByRole("group").querySelector("blockquote")?.textContent,
  ).toBe(email.body);
});
test("Model Lab preserves failed quality gate and separate language evidence", async () => {
  await open("/lab");
  expect(await screen.findByText(/Quality gate FAILED/)).toBeVisible();
  expect(screen.getByText(/English: 20\/56/)).toBeVisible();
  expect(screen.getByText(/Arabic-heavy: 1\/11/)).toBeVisible();
});
test("missing model gives explicit failure with no invented prediction", async () => {
  const user = await open("/intelligence");
  vi.mocked(fetch).mockResolvedValueOnce(
    Response.json({ detail: { code: "model_unavailable" } }, { status: 503 }),
  );
  await user.click(screen.getByRole("button", { name: "Run prediction" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "no canned result",
  );
  expect(screen.queryByLabelText("Analysis result")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Run prediction" })).toBeEnabled();
});
test("language toggles RTL and no Gmail/session requests are issued", async () => {
  const user = await open("/tasks");
  expect(document.documentElement.dir).toBe("ltr");
  await user.click(screen.getByRole("button", { name: "التبديل للعربية" }));
  await waitFor(() => expect(document.documentElement.dir).toBe("rtl"));
  expect(screen.getByRole("button", { name: "استخرج المهام" })).toBeVisible();
  expect(calls.every((c) => !/(gmail|auth|session)/.test(c.url))).toBe(true);
});

test("navigation preserves the selected source query", async () => {
  const user = await open("/tasks?email=1");
  const link = screen.getByRole("link", { name: "Email Intelligence" });
  expect(link).toHaveAttribute("href", "/intelligence?email=1");
  await user.click(link);
  expect(screen.getByLabelText("Text")).toHaveValue(email.body);
});
