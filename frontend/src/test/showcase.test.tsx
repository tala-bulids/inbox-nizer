import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import comparison from "../../../docs/phase2/evidence/experiment-comparison.json";
import dataset from "../../../docs/phase2/evidence/dataset-card.json";
import configuration from "../../../docs/phase2/evidence/training-configuration.json";
import historical from "../../../docs/release/v03-v10-20261024.json";
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
    if (path.endsWith("predict"))
      return Response.json({
        predictions: [{ category: "Events & Invitations", confidence: 0.6 }],
        summary: "Please submit the form.",
        classifier_status: "experimental",
        summary_method: "extractive",
        model_version: "phase2-A",
        artifact_sha256: comparison.runs[0]!.run.artifact_sha256,
        processing_ms: 12.5,
        cold_load_included: false,
        score_semantics: "Raw score",
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
    if (path.endsWith("portfolio"))
      return Response.json({
        selected: comparison.selected_research_candidate,
        models: comparison.runs.map((row) => ({
          id: row.run.candidate,
          run: row.run,
          metrics: row.metrics,
          history: row.training_history,
        })),
        dataset,
        configuration,
        historical: {
          development: historical.fresh_development_metrics,
          languages: {
            English: { n: 56, correct: 20 },
            "Arabic-heavy": { n: 11, correct: 1 },
          },
        },
        rag: {
          memory_mib: 880.27,
          qa: { n: 20, retrieval: { "recall@5": 0.7619 } },
        },
        evidence_version: "phase2@5b7cf7b + phase3@96fc1c0",
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
  expect(screen.getByLabelText("Filter collection")).toBeVisible();
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
  await screen.findByRole("link", { name: "Email Collection" });
  if (path.startsWith("/intelligence"))
    await user.click(await screen.findByRole("button", { name: "Playground" }));
  if (!path.startsWith("/lab") && !path.startsWith("/intelligence"))
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
    await screen.findByRole("region", { name: "Answer" }),
  ).toHaveTextContent("Workshop date: 2026-11-05 [email_id=1]");
  expect(screen.getByRole("link", { name: /Open source/ })).toHaveAttribute(
    "href",
    "/collection?email=1",
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
  expect(calls.some((c) => c.url.endsWith("predict"))).toBe(false);
  await user.clear(screen.getByLabelText("Text"));
  await user.type(
    screen.getByLabelText("Text"),
    "Please review this fictional report.",
  );
  await user.click(screen.getByRole("button", { name: "Run prediction" }));
  expect(await screen.findByText(/Events & Invitations/)).toBeVisible();
  expect(
    JSON.parse(String(calls.find((c) => c.url.endsWith("predict"))?.init?.body))
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
  const user = await open("/lab");
  await user.click(await screen.findByRole("button", { name: "Evaluation" }));
  expect(await screen.findByText(/quality gate FAILED/)).toBeVisible();
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
  const link = screen.getByRole("link", {
    name: "Email Collection",
  });
  expect(link).toHaveAttribute("href", "/collection?email=1");
  await user.click(link);
  expect(screen.getByLabelText("Choose a source")).toHaveValue("1");
});

test("Model Lab uses saved metrics, changes experiments, and never invents loss curves", async () => {
  const user = await open("/lab");
  await user.click(
    await screen.findByRole("button", { name: "Training & data" }),
  );
  expect(
    await screen.findByText(/Epoch loss curves: Not available/),
  ).toBeVisible();
  expect(screen.getByText("0.1423")).toBeVisible();
  expect(screen.getByText("0.1894")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Evaluation" }));
  expect(await screen.findByText("88.4%")).toBeVisible();
  expect(
    screen.getByText(/Selected model Arabic: Not evaluated/),
  ).toBeVisible();
  await user.selectOptions(screen.getByLabelText("Inspect experiment"), "C");
  expect(screen.getByText("83.7%")).toBeVisible();
  await user.click(screen.getByText("Confusion matrix", { exact: true }));
  expect(screen.getByRole("region", { name: "Confusion table" })).toBeVisible();
  await user.selectOptions(screen.getByLabelText("Inspect experiment"), "B");
  expect(screen.getByText(/Excluded: unknown historical/)).toBeVisible();
});

test("inline citations and collection filtering expose original source records", async () => {
  const user = await open();
  await user.click(
    screen.getByRole("button", { name: "What is the Atlas workshop date?" }),
  );
  await user.click(screen.getByRole("button", { name: "Ask AI" }));
  await user.click(await screen.findByRole("link", { name: "Source 1" }));
  await user.type(screen.getByLabelText("Filter collection"), "nonexistent");
  expect(screen.getByText("No matching messages")).toBeVisible();
  await user.clear(screen.getByLabelText("Filter collection"));
  expect(
    screen.getByRole("link", { name: /Atlas workshop EN/ }),
  ).toHaveAttribute("href", "/collection?email=1");
});

test("prediction input is bounded, uncalibrated and cleared after leaving the playground", async () => {
  const user = await open("/intelligence");
  expect(await screen.findByLabelText("Text")).toHaveAttribute(
    "maxlength",
    "6000",
  );
  await user.click(screen.getByRole("button", { name: "Run prediction" }));
  expect(
    await screen.findByText(/Raw model score is not a probability/),
  ).toBeVisible();
  expect(screen.getByText(/phase2-A · 12.5 ms/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Models" }));
  expect(screen.queryByLabelText("Analysis result")).not.toBeInTheDocument();
});

test("pending prediction prevents duplicate submits and recovers after rate limiting", async () => {
  const user = await open("/intelligence");
  let resolve!: (response: Response) => void;
  vi.mocked(fetch).mockImplementationOnce(
    () =>
      new Promise<Response>((done) => {
        resolve = done;
      }),
  );
  await user.click(screen.getByRole("button", { name: "Run prediction" }));
  expect(screen.getByRole("button", { name: "Analyzing…" })).toBeDisabled();
  resolve(Response.json({ detail: { code: "rate_limited" } }, { status: 429 }));
  expect(await screen.findByRole("alert")).toHaveTextContent("retry shortly");
  expect(screen.getByRole("button", { name: "Run prediction" })).toBeEnabled();
  expect(screen.queryByLabelText("Analysis result")).not.toBeInTheDocument();
});

test("invalid model input explains recovery without echoing input", async () => {
  const user = await open("/intelligence");
  vi.mocked(fetch).mockResolvedValueOnce(
    Response.json({ code: "invalid_input" }, { status: 422 }),
  );
  await user.click(screen.getByRole("button", { name: "Run prediction" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Shorten it and retry",
  );
});
