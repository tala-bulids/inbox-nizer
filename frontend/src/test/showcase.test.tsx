import { render, screen, waitFor, within } from "@testing-library/react";
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
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
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
        serving_runtime: { id: "e5-int8-fp32-corpus-v1" },
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
          tasks: { f1: 1 },
          qa: { n: 20, retrieval: { "recall@5": 0.7619 } },
        },
        evidence_version: "phase2@5b7cf7b + phase3@96fc1c0",
      });
    throw new Error("Unexpected route");
  });
});

afterEach(() => vi.restoreAllMocks());
async function open(path = "/ask") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <ShowcaseApp />
    </MemoryRouter>,
  );
  await user.click(screen.getByRole("button", { name: "Switch to English" }));
  if (["/lab", "/intelligence"].some((p) => path.startsWith(p))) {
    await screen.findByRole("heading", { name: "The idea" });
    if (path.startsWith("/intelligence"))
      await user.click(screen.getByRole("button", { name: "Playground" }));
  } else if (path !== "/") await screen.findByLabelText("Choose a source");
  return user;
}
test("homepage introduces the project and both calls to action work", async () => {
  const user = await open("/");
  expect(
    screen.getByRole("heading", { name: "Inbox-nizer", level: 1 }),
  ).toBeVisible();
  expect(
    screen.getByText(/not a service for managing your personal email/),
  ).toBeVisible();
  await user.click(screen.getByRole("link", { name: /Try the project/ }));
  expect(await screen.findByLabelText("Your question")).toBeVisible();
  await user.click(screen.getByRole("link", { name: "Home" }));
  await user.click(screen.getByRole("link", { name: "Explore Model Lab" }));
  expect(
    await screen.findByRole("heading", { name: "The idea" }),
  ).toBeVisible();
});
test("Ask keeps real request contract and separates answer from cited source", async () => {
  const user = await open();
  await user.click(
    screen.getByRole("button", { name: "What is the Atlas workshop date?" }),
  );
  await user.click(screen.getByRole("button", { name: "Ask" }));
  const answer = await screen.findByRole("region", { name: "Answer" });
  expect(answer).toHaveTextContent("Workshop date: 2026-11-05");
  expect(answer).not.toHaveTextContent("email_id");
  expect(
    screen.getByRole("region", { name: "Supporting messages" }),
  ).toBeVisible();
  await user.click(
    screen.getByText("Atlas workshop", { selector: "summary span" }),
  );
  expect(
    screen.getByRole("link", { name: "Open source message" }),
  ).toHaveAttribute("href", "/collection?email=1");
  expect(
    calls.every(
      (c) =>
        c.url.startsWith("/api/showcase/") && c.init?.credentials === "omit",
    ),
  ).toBe(true);
  expect(
    JSON.parse(String(calls.find((c) => c.url.endsWith("ask"))?.init?.body)),
  ).toEqual({ question: "What is the Atlas workshop date?", mode: "grounded" });
  await user.click(screen.getByRole("link", { name: "Source 1" }));
  expect(screen.getByLabelText("Choose a source")).toHaveValue("1");
});
test("insufficient evidence is localized without presenting retrieval as an answer", async () => {
  const user = await open();
  vi.mocked(fetch).mockResolvedValueOnce(
    Response.json({
      status: "insufficient_evidence",
      answer: "Backend fallback",
      mode: "retrieval_only",
      verification: "no_verified_answer",
      sources: [],
    }),
  );
  await user.type(screen.getByLabelText("Your question"), "Unknown question");
  await user.click(screen.getByRole("button", { name: "Ask" }));
  expect(
    await screen.findByText(/couldn't find enough information/),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "التبديل للعربية" }));
  expect(
    screen.getByText("لم أجد معلومات كافية في الرسائل للإجابة عن هذا السؤال."),
  ).toBeVisible();
  expect(screen.queryByText("Backend fallback")).not.toBeInTheDocument();
});
test("tasks preserve deadlines and evidence without invented priority", async () => {
  const user = await open("/tasks");
  await user.click(screen.getByRole("button", { name: "Extract tasks" }));
  expect(await screen.findByText("Submit the form")).toBeVisible();
  expect(screen.getByText("Maya")).toBeVisible();
  expect(screen.getByText("2026-11-02", { selector: "dd bdi" })).toBeVisible();
  expect(
    screen.queryByText(/Priority|Rule strength|Deadline state|UTC/),
  ).not.toBeInTheDocument();
  await user.click(screen.getByText("Original source"));
  expect(
    screen.getByRole("group").querySelector("blockquote")?.textContent,
  ).toBe(email.body);
  await user.click(screen.getByRole("link", { name: "Open supporting email" }));
  expect(screen.getByLabelText("Filter collection")).toBeVisible();
});
test("missing or conditional task deadlines are not invented or hidden", async () => {
  const user = await open("/tasks");
  vi.mocked(fetch).mockResolvedValueOnce(
    Response.json({
      method: "rules",
      tasks: [
        {
          email_id: 1,
          task: "Review if approved",
          confidence: 0.9,
          deadline_date: null,
          deadline_text: null,
          deadline_state: "missing",
          responsible: null,
          conditional: true,
          state: "superseded",
          superseded_by: [2],
          evidence: { subject: email.subject, body: email.body },
        },
      ],
    }),
  );
  await user.click(screen.getByRole("button", { name: "Extract tasks" }));
  expect(await screen.findByText("Not stated in the message")).toBeVisible();
  expect(screen.getByText(/depends on a condition/)).toBeVisible();
  expect(screen.getByText(/cancelled in a later message/)).toBeVisible();
  expect(screen.getByRole("link", { name: "View update" })).toHaveAttribute(
    "href",
    "/collection?email=2",
  );
});
test("Model Lab distinguishes deployed pipeline and Linux qualification", async () => {
  const user = await open("/lab");
  expect(screen.getByText(/ONNX INT8/)).toBeVisible();
  expect(screen.getByText(/not a separately trained model/)).toBeVisible();
  expect(screen.getByText(/500.01/)).toBeVisible();
  expect(screen.getByText(/333.14/)).toBeVisible();
  expect(screen.getByText(/3.90 to 6.60 seconds/)).toBeVisible();
  expect(
    screen.queryByText(/hosting acceptance remain open|e5-int8-fp32-corpus-v1/),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "التبديل للعربية" }));
  expect(
    screen.getByRole("heading", { name: "النموذج المستخدم في الموقع" }),
  ).toBeVisible();
});
test("training keeps real saved loss, data separation and historical fine-tuning limits", async () => {
  const user = await open("/lab");
  await user.click(screen.getByRole("button", { name: "Training & data" }));
  expect(screen.getByText(/24 fictional messages are separate/)).toBeVisible();
  expect(
    screen.getByText(/did not train DistilBERT from scratch/),
  ).toBeVisible();
  await user.click(screen.getByText("Training details & reproducibility"));
  expect(screen.getByText(/No epoch-by-epoch loss curves/)).toBeVisible();
  expect(screen.getByText("0.1423")).toBeVisible();
  expect(screen.getByText("0.1894")).toBeVisible();
});
test("evaluation keeps verified metrics and separates excluded historical results", async () => {
  const user = await open("/lab");
  await user.click(screen.getByRole("button", { name: "Evaluation" }));
  const table = screen.getByRole("region", { name: "Classifier comparison" });
  expect(within(table).getByText("88.4%")).toBeVisible();
  expect(within(table).getByText("83.7%")).toBeVisible();
  expect(within(table).queryByText("DistilBERT")).not.toBeInTheDocument();
  expect(screen.getByText("76.2%")).toBeVisible();
  expect(screen.getByText("1.00")).toBeVisible();
  await user.click(screen.getByText("Detailed metrics & errors"));
  expect(screen.getByText(/quality gate failed/)).toBeVisible();
  expect(screen.getByText(/20\/56/)).toBeVisible();
  expect(screen.getByText(/1\/11/)).toBeVisible();
  await user.selectOptions(screen.getByLabelText("Inspect experiment"), "B");
  expect(
    screen.getByText(/Historical result excluded from selection/),
  ).toBeVisible();
  await user.click(screen.getByText("Confusion matrix", { exact: true }));
  expect(screen.getByRole("region", { name: "Confusion table" })).toBeVisible();
});
test("prediction remains editable, bounded and cleared when leaving playground", async () => {
  const user = await open("/intelligence");
  expect(calls.some((c) => c.url.endsWith("predict"))).toBe(false);
  expect(screen.getByLabelText("Text")).toHaveAttribute("maxlength", "6000");
  await user.clear(screen.getByLabelText("Text"));
  await user.type(
    screen.getByLabelText("Text"),
    "Please review this fictional report.",
  );
  await user.click(screen.getByRole("button", { name: "Run prediction" }));
  expect(await screen.findByText("Events & Invitations")).toBeVisible();
  expect(screen.getByText(/not a probability of correctness/)).toBeVisible();
  expect(screen.getByText(/12.5 ms/)).toBeVisible();
  expect(screen.queryByText(/phase2-A/)).not.toBeInTheDocument();
  expect(
    JSON.parse(String(calls.find((c) => c.url.endsWith("predict"))?.init?.body))
      .body,
  ).toBe("Please review this fictional report.");
  await user.click(screen.getByRole("button", { name: "Overview" }));
  expect(screen.queryByLabelText("Analysis result")).not.toBeInTheDocument();
});
test.each([
  [503, "model is unavailable"],
  [422, "Shorten it and retry"],
])(
  "prediction failure %s gives recovery without invented results",
  async (status, message) => {
    const user = await open("/intelligence");
    vi.mocked(fetch).mockResolvedValueOnce(
      Response.json({ detail: "unavailable" }, { status }),
    );
    await user.click(screen.getByRole("button", { name: "Run prediction" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.queryByLabelText("Analysis result")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Run prediction" }),
    ).toBeEnabled();
  },
);
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
  resolve(Response.json({ detail: "busy" }, { status: 429 }));
  expect(await screen.findByRole("alert")).toHaveTextContent("retry shortly");
  expect(screen.getByRole("button", { name: "Run prediction" })).toBeEnabled();
});
test("navigation preserves source and collection filtering remains usable", async () => {
  const user = await open("/tasks?email=1");
  const link = screen.getByRole("link", { name: "Email Collection" });
  expect(link).toHaveAttribute("href", "/collection?email=1");
  await user.click(link);
  await user.type(screen.getByLabelText("Filter collection"), "nonexistent");
  expect(screen.getByText("No matching messages")).toBeVisible();
  await user.clear(screen.getByLabelText("Filter collection"));
  expect(
    screen.getByRole("link", { name: /Atlas workshop learning/ }),
  ).toHaveAttribute("href", "/collection?email=1");
});
test("Arabic labels and RTL remain consistent without Gmail requests or reference metadata", async () => {
  const user = await open("/tasks");
  expect(document.documentElement.dir).toBe("ltr");
  await user.click(screen.getByRole("button", { name: "التبديل للعربية" }));
  await waitFor(() => expect(document.documentElement.dir).toBe("rtl"));
  expect(screen.getByRole("heading", { name: "المهام" })).toBeVisible();
  expect(screen.getByLabelText("اختر رسالة")).toBeVisible();
  expect(
    screen.queryByText(/UTC|تاريخ المجموعة المرجعي/),
  ).not.toBeInTheDocument();
  expect(calls.every((c) => !/(gmail|auth|session)/.test(c.url))).toBe(true);
});
