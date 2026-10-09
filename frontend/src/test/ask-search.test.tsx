import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate, useLocation } from "react-router-dom";
import { http, HttpResponse, delay } from "msw";
import { App } from "../app/App";
import { server, base } from "./server";
import { email, supported, generated, clarification } from "./fixtures";
function History() {
  const go = useNavigate();
  const loc = useLocation();
  return (
    <>
      <button onClick={() => go(-1)}>Back test</button>
      <span data-testid="url">{loc.pathname + loc.search}</span>
    </>
  );
}
async function open(path = "/ask") {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[path]}>
      <History />
      <App />
    </MemoryRouter>,
  );
  await user.type(screen.getByLabelText("رمز الوصول التطويري"), "test-token");
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  await screen.findByRole("navigation", { name: "التنقل الرئيسي" });
  return user;
}
async function submit() {
  const user = await open();
  await user.type(screen.getByLabelText("سؤالك"), "متى موعد التسجيل؟");
  await user.click(screen.getByRole("button", { name: "اسأل البريد" }));
  return user;
}
const result = (
  subject = "Synthetic result",
  matched_text = "نص مطابق Mixed English <img src=x onerror=alert(1)>",
) => ({
  query: "test",
  count: 1,
  results: [
    {
      email: { id: 11, subject, from: "فريق Team <demo@example.invalid>" },
      matched_text,
      score: 0.98765,
    },
  ],
});
test("Ask starts calmly, blank submit is guarded and Enter creates newline", async () => {
  let calls = 0;
  server.use(
    http.post(base + "/ask", () => {
      calls++;
      return HttpResponse.json(supported);
    }),
  );
  const user = await open();
  expect(screen.getByText("ما الذي تريد معرفته؟")).toBeVisible();
  expect(screen.getByRole("button", { name: "اسأل البريد" })).toBeDisabled();
  const input = screen.getByLabelText("سؤالك");
  fireEvent.submit(input.closest("form")!);
  await user.type(input, "   {Enter}");
  expect(calls).toBe(0);
  expect(input).toHaveValue("   \n");
});
test("Ctrl Enter submits once and shows original question while loading", async () => {
  let calls = 0;
  server.use(
    http.post(base + "/ask", async () => {
      calls++;
      await delay(300);
      return HttpResponse.json(supported);
    }),
  );
  const user = await open();
  await user.type(screen.getByLabelText("سؤالك"), "موعد الطلب");
  await user.keyboard("{Control>}{Enter}{/Control}");
  fireEvent.submit(screen.getByLabelText("سؤالك").closest("form")!);
  expect(await screen.findByRole("status")).toHaveTextContent("جارٍ التحميل");
  expect(screen.getByText("السؤال المُرسل")).toBeVisible();
  await screen.findByText("مدعوم من البريد");
  expect(calls).toBe(1);
  expect(screen.getByTestId("url")).toHaveTextContent("/ask");
});
test.each(["deterministic_fact", "extractive"])(
  "supported %s retains source marker and source cards",
  async (mode) => {
    server.use(
      http.post(base + "/ask", () =>
        HttpResponse.json({ ...supported, answer_mode: mode }),
      ),
    );
    await submit();
    expect(await screen.findByText("مدعوم من البريد")).toBeVisible();
    expect(screen.getByText("ليس تحققًا مستقلًا من الحقيقة")).toBeVisible();
    expect(
      screen.getByRole("link", { name: new RegExp(email.subject) }),
    ).toHaveAttribute("href", "/email/11");
    expect(screen.getByText(email.from)).toBeVisible();
  },
);
test.each([
  { answer_mode: undefined, verification: undefined },
  { answer_mode: "future_mode", verification: "source_supported" },
  { answer_mode: "extractive", verification: "future_state" },
  { answer_mode: "generated_synthesis", verification: "source_supported" },
  { answer_mode: "extractive", verification: "not_semantically_verified" },
])("unknown or conflicting metadata never promoted", async (meta) => {
  server.use(
    http.post(base + "/ask", () =>
      HttpResponse.json({ ...supported, ...meta }),
    ),
  );
  await submit();
  expect(await screen.findByRole("note")).toHaveTextContent(
    "قد يُسقط النص شروطًا",
  );
  expect(screen.queryByText("مدعوم من البريد")).not.toBeInTheDocument();
});
test("inconsistent citations suppress support marker and fabricated source links", async () => {
  server.use(
    http.post(base + "/ask", () =>
      HttpResponse.json({
        ...supported,
        citations: [{ email_id: 999 }, { email_id: -1 }],
      }),
    ),
  );
  await submit();
  await screen.findByRole("note");
  expect(screen.queryByText("مدعوم من البريد")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: new RegExp(email.subject) }),
  ).not.toBeInTheDocument();
});
test("generated text preserves backend notice, safe Arabic and mixed text", async () => {
  const answer =
    generated.answer + "\nموعدك 11:35 ABC123 <script>unsafe()</script>";
  server.use(
    http.post(base + "/ask", () => HttpResponse.json({ ...generated, answer })),
  );
  const user = await submit();
  const rendered = await screen.findByText(
    /Generated synthesis, not a semantically verified extraction/,
  );
  expect(rendered.textContent).toBe(answer);
  expect(rendered).toHaveAttribute("dir", "auto");
  expect(screen.getByRole("note")).toHaveTextContent("استثناءات");
  expect(document.querySelector(".answer-panel script")).toBeNull();
  await user.click(
    screen.getByRole("link", { name: new RegExp(email.subject) }),
  );
  await screen.findByText("نص البريد الأصلي المخزن");
});
test("clarification is bounded and follows original question with loading to result", async () => {
  const bodies: unknown[] = [];
  server.use(
    http.post(base + "/ask", async ({ request }) => {
      bodies.push(await request.json());
      if (bodies.length === 1)
        return HttpResponse.json({
          ...clarification,
          clarification_options: [
            { email_id: -1, subject: "invalid" },
            ...Array.from({ length: 7 }, (_, i) => ({
              email_id: i + 11,
              subject: "اختيار " + i,
              date: "2026-10-08",
            })),
          ],
        });
      await delay(250);
      return HttpResponse.json(supported);
    }),
  );
  const user = await submit();
  await screen.findByText("لنحدد البريد المقصود");
  expect(screen.getAllByRole("button", { name: /اختيار/ })).toHaveLength(5);
  expect(screen.queryByText("invalid")).not.toBeInTheDocument();
  await user.clear(screen.getByLabelText("سؤالك"));
  await user.type(screen.getByLabelText("سؤالك"), "draft changed");
  await user.click(screen.getByRole("button", { name: /اختيار 0/ }));
  await screen.findByRole("status");
  await screen.findByText("مدعوم من البريد");
  expect(bodies).toEqual([
    { question: "متى موعد التسجيل؟" },
    { question: "متى موعد التسجيل؟", email_id: 11 },
  ]);
  expect(screen.queryByText("لنحدد البريد المقصود")).not.toBeInTheDocument();
});
test("insufficient evidence ignores any stray sources and stays non-error", async () => {
  server.use(
    http.post(base + "/ask", () =>
      HttpResponse.json({
        ...supported,
        status: "insufficient_evidence",
        answer: "لا توجد معلومات كافية",
      }),
    ),
  );
  await submit();
  await screen.findByText("لا توجد أدلة كافية");
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: new RegExp(email.subject) }),
  ).not.toBeInTheDocument();
});
test.each([422, 503])(
  "Ask %s error is normalized and not retried automatically",
  async (status) => {
    let calls = 0;
    server.use(
      http.post(base + "/ask", () => {
        calls++;
        return HttpResponse.json({ detail: "PRIVATE_ERROR" }, { status });
      }),
    );
    await submit();
    const error = await screen.findByRole("alert");
    expect(error).not.toHaveTextContent("PRIVATE_ERROR");
    expect(screen.queryByText("لا توجد أدلة كافية")).not.toBeInTheDocument();
    expect(calls).toBe(1);
  },
);
test.each(["network", "contract"])("Ask %s error is safe", async (kind) => {
  server.use(
    http.post(base + "/ask", () =>
      kind === "network"
        ? HttpResponse.error()
        : HttpResponse.json({ answer: 123 }),
    ),
  );
  await submit();
  expect(await screen.findByRole("alert")).toBeVisible();
});
test("Ask 401 logs out and does not carry question into next session", async () => {
  server.use(
    http.post(base + "/ask", () => new HttpResponse(null, { status: 401 })),
  );
  const user = await submit();
  await screen.findByLabelText("رمز الوصول التطويري");
  await user.type(screen.getByLabelText("رمز الوصول التطويري"), "next-token");
  await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
  expect(await screen.findByLabelText("سؤالك")).toHaveValue("");
  expect(screen.queryByText("السؤال المُرسل")).not.toBeInTheDocument();
});
test("leaving Ask aborts an active request and late answer cannot reappear", async () => {
  let aborted = false;
  server.use(
    http.post(base + "/ask", async ({ request }) => {
      request.signal.addEventListener("abort", () => {
        aborted = true;
      });
      await delay(400);
      return HttpResponse.json(supported);
    }),
  );
  const user = await submit();
  await screen.findByRole("status");
  await user.click(screen.getByRole("link", { name: "البحث" }));
  await waitFor(() => expect(aborted).toBe(true));
  await user.click(screen.getByRole("link", { name: "اسأل البريد" }));
  expect(await screen.findByText("ما الذي تريد معرفته؟")).toBeVisible();
  expect(screen.queryByText("مدعوم من البريد")).not.toBeInTheDocument();
});
test("Search initial is distinct, blank submit and typing do not request", async () => {
  let calls = 0;
  server.use(
    http.get(base + "/search/semantic", () => {
      calls++;
      return HttpResponse.json(result());
    }),
  );
  const user = await open("/search");
  expect(screen.getByText("ابدأ بوصف ما تتذكره")).toBeVisible();
  expect(screen.queryByText("لا توجد نتائج")).not.toBeInTheDocument();
  fireEvent.submit(screen.getByRole("search"));
  await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "travel");
  expect(calls).toBe(0);
});
test("Search loading then safe results, no similarity percentage or invented date", async () => {
  server.use(
    http.get(base + "/search/semantic", async ({ request }) => {
      expect(new URL(request.url).searchParams.get("limit")).toBe("10");
      await delay(250);
      return HttpResponse.json(result());
    }),
  );
  const user = await open("/search");
  await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "رحلة");
  await user.click(screen.getByRole("button", { name: "بحث" }));
  await screen.findByRole("status");
  await screen.findByText("Synthetic result");
  const snippet = screen.getByText(/نص مطابق Mixed/);
  expect(snippet).toHaveAttribute("dir", "auto");
  expect(document.querySelector(".search-results img")).toBeNull();
  expect(screen.queryByText(/98.765|98%/)).not.toBeInTheDocument();
  expect(document.querySelector(".search-results time")).toBeNull();
  expect(screen.getByTestId("url")).toHaveTextContent("/search");
});
test("Search detail and back preserves private submitted query, result and edited draft", async () => {
  let calls = 0;
  server.use(
    http.get(base + "/search/semantic", () => {
      calls++;
      return HttpResponse.json(result());
    }),
  );
  const user = await open("/search");
  await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "submitted");
  await user.click(screen.getByRole("button", { name: "بحث" }));
  await screen.findByText("Synthetic result");
  await user.clear(screen.getByLabelText("ما الذي تبحث عنه؟"));
  await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "new draft");
  await user.click(screen.getByRole("link", { name: /Synthetic result/ }));
  await screen.findByText(email.body);
  await user.click(screen.getByRole("button", { name: "Back test" }));
  expect(await screen.findByText("Synthetic result")).toBeVisible();
  expect(screen.getByLabelText("ما الذي تبحث عنه؟")).toHaveValue("new draft");
  expect(screen.getByText("submitted")).toBeVisible();
  expect(calls).toBe(1);
  expect(localStorage.length + sessionStorage.length).toBe(0);
});
test("Search zero results is a completed state", async () => {
  server.use(
    http.get(base + "/search/semantic", () =>
      HttpResponse.json({ query: "x", count: 0, results: [] }),
    ),
  );
  const user = await open("/search");
  await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "x");
  await user.click(screen.getByRole("button", { name: "بحث" }));
  expect(await screen.findByText("لا توجد نتائج")).toBeVisible();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
test.each(["network", "backend", "contract"])(
  "Search %s failure differs from empty",
  async (kind) => {
    server.use(
      http.get(base + "/search/semantic", () =>
        kind === "network"
          ? HttpResponse.error()
          : kind === "backend"
            ? HttpResponse.json({ detail: "PRIVATE" }, { status: 503 })
            : HttpResponse.json({ results: 42 }),
      ),
    );
    const user = await open("/search");
    await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "x");
    await user.click(screen.getByRole("button", { name: "بحث" }));
    expect(await screen.findByRole("alert")).not.toHaveTextContent("PRIVATE");
    expect(screen.queryByText("لا توجد نتائج")).not.toBeInTheDocument();
  },
);
test("replacement Search aborts old query and late result cannot overwrite new result", async () => {
  let aborted = false;
  server.use(
    http.get(base + "/search/semantic", async ({ request }) => {
      const q = new URL(request.url).searchParams.get("q");
      if (q === "old") {
        request.signal.addEventListener("abort", () => {
          aborted = true;
        });
        await delay(300);
        return HttpResponse.json(result("OLD_RESULT"));
      }
      return HttpResponse.json(result("NEW_RESULT"));
    }),
  );
  const user = await open("/search");
  await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "old");
  await user.click(screen.getByRole("button", { name: "بحث" }));
  await screen.findByRole("status");
  await user.clear(screen.getByLabelText("ما الذي تبحث عنه؟"));
  await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "new");
  await user.click(screen.getByRole("button", { name: "بحث" }));
  await screen.findByText("NEW_RESULT");
  await waitFor(() => expect(aborted).toBe(true));
  expect(screen.queryByText("OLD_RESULT")).not.toBeInTheDocument();
});
test.each(["/ask", "/search"])(
  "logout clears private interaction at %s",
  async (route) => {
    const user = await open(route);
    if (route === "/ask") {
      await user.type(screen.getByLabelText("سؤالك"), "PRIVATE_Q");
      await user.click(screen.getByRole("button", { name: "اسأل البريد" }));
      await screen.findByText("مدعوم من البريد");
    } else {
      await user.type(screen.getByLabelText("ما الذي تبحث عنه؟"), "PRIVATE_Q");
      await user.click(screen.getByRole("button", { name: "بحث" }));
      await screen.findByText("Original matched source text");
    }
    await user.click(screen.getByRole("button", { name: "خروج" }));
    await user.type(screen.getByLabelText("رمز الوصول التطويري"), "next-token");
    await user.click(screen.getByRole("button", { name: "فتح مساحة العمل" }));
    expect(
      await screen.findByLabelText(
        route === "/ask" ? "سؤالك" : "ما الذي تبحث عنه؟",
      ),
    ).toHaveValue("");
    expect(screen.queryByText("PRIVATE_Q")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Original matched source text"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("مدعوم من البريد")).not.toBeInTheDocument();
  },
);
