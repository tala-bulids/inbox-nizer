import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { LocaleProvider, useLocale } from "../app/locale";
import { AnswerView } from "../features/ask/AnswerView";
import {
  conversationalAnswer,
  readableAnswer,
} from "../features/ask/presentation";
import { supported, generated } from "./fixtures";
import type { AskAnswer } from "../api/ask";

function Language() {
  const { toggle } = useLocale();
  return <button onClick={toggle}>Language</button>;
}
function open(answer: AskAnswer, question?: string) {
  render(
    <MemoryRouter>
      <LocaleProvider>
        <Language />
        <AnswerView answer={answer} question={question} onClarify={() => {}} />
      </LocaleProvider>
    </MemoryRouter>,
  );
}
function matching(): AskAnswer {
  const sources = [1, 2, 3, 4, 5].map((id) => ({
    ...supported.sources[0]!,
    email_id: id,
    subject: `Weekly edition ${id}`,
    from: "Community <news@example.invalid>",
    date: `2026-10-${String(11 - id).padStart(2, "0")}T12:00:00+00:00`,
  }));
  return {
    ...supported,
    answer_mode: "extractive",
    sources,
    citations: sources.map((s) => ({ email_id: s.email_id })),
    answer:
      "رسائل مرتبطة بسؤالك — مقتطفات من البريد: " +
      sources
        .map(
          (s) =>
            `- ${s.date}: وجدت رسالة من Community news@example.invalid: ${s.subject} [email_id=${s.email_id}]`,
        )
        .join("\n"),
  };
}

test("matching emails become a concise Arabic response with collapsed working source links", async () => {
  const user = userEvent.setup();
  const answer = matching();
  const original = JSON.stringify(answer);
  open(answer);
  const main = screen.getByTestId("conversational-answer");
  expect(main).toHaveTextContent("نعم، وجدت");
  expect(main).toHaveTextContent("Community");
  expect(main).toHaveTextContent("أكتوبر");
  expect(main.textContent).not.toMatch(
    /email_id|chunk_id|2026-10-10T|news@example|Weekly edition/,
  );
  expect(
    screen.getByText("المصادر (5)").closest("details"),
  ).not.toHaveAttribute("open");
  expect(screen.getAllByRole("link")[0]).not.toBeVisible();
  await user.click(screen.getByText("المصادر (5)"));
  const link = screen.getByRole("link", { name: /Weekly edition 1/ });
  expect(link).toHaveAttribute("href", "/email/1");
  expect(link).toHaveTextContent("فتح البريد");
  expect(link).not.toHaveTextContent("#1");
  expect(JSON.stringify(answer)).toBe(original);
});

test("language selection formats summary and dates in English", async () => {
  const user = userEvent.setup();
  open(matching());
  await user.click(screen.getByText("Language"));
  expect(screen.getByTestId("conversational-answer")).toHaveTextContent(
    "Yes, I found 5 matching emails",
  );
  expect(screen.getByTestId("conversational-answer")).toHaveTextContent(
    "10 October 2026",
  );
  expect(screen.getByText("Sources (5)")).toBeVisible();
});

test("missing dates do not invent a latest date or sender organization", () => {
  const answer = matching();
  answer.sources[0]!.date = "";
  answer.sources[0]!.from = "different@example.invalid";
  open(answer);
  expect(screen.getByTestId("conversational-answer").textContent).not.toMatch(
    /أحدث|Community|Skool/,
  );
});

test("conditional supported facts preserve negation and exceptions while hiding markers", () => {
  const answer = {
    ...supported,
    answer:
      "Pay by 2026-10-22 unless already paid; do not pay twice. [email_id=11]",
  };
  open(answer);
  const main = screen.getByTestId("conversational-answer");
  expect(main).toHaveTextContent("unless already paid; do not pay twice.");
  expect(main.textContent).not.toMatch(/email_id|2026-10-22/);
  expect(main).toHaveTextContent("أكتوبر");
  expect(screen.getByText("مدعوم من البريد")).toBeVisible();
});

test("generated synthesis warning and all generated conditions stay visible", () => {
  open({
    ...generated,
    answer:
      generated.answer + " Only if approved; unless revoked. [email_id=11]",
  });
  expect(screen.getByRole("note")).toHaveTextContent("قد يُسقط النص شروطًا");
  expect(screen.getByTestId("conversational-answer")).toHaveTextContent(
    "Only if approved; unless revoked.",
  );
  expect(screen.getByTestId("conversational-answer").textContent).not.toContain(
    "[email_id=",
  );
});

test("unknown verification does not enable metadata summary", () => {
  const answer = matching();
  delete answer.verification;
  open(answer);
  expect(screen.queryByText("مدعوم من البريد")).not.toBeInTheDocument();
  expect(screen.getByRole("note")).toBeVisible();
});

test("multi-email answers retain substantive facts and exceptions without metadata wrappers", () => {
  const answer = matching();
  answer.answer = answer.answer.replaceAll(
    /وجدت رسالة من Community news@example.invalid: Weekly edition \d/g,
    "Payment is due unless already paid.",
  );
  const compact = conversationalAnswer(answer, answer.sources, "en", true);
  expect(compact).not.toContain("Titles include");
  expect(compact).toContain("Payment is due unless already paid.");
  expect(compact).not.toMatch(/email_id|2026-10-10T|مقتطفات من البريد/);
  const detailed = conversationalAnswer(
    answer,
    answer.sources,
    "en",
    true,
    "show details",
  );
  expect(detailed).toContain("unless already paid");
  expect(detailed).not.toMatch(/email_id|2026-10-10T/);
});

test("inconsistent citations never produce clickable unapproved sources", () => {
  open({ ...supported, citations: [{ email_id: 999 }] });
  expect(screen.queryByText("مدعوم من البريد")).not.toBeInTheDocument();
  expect(screen.getByText("المصادر (0)")).toBeVisible();
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});

test("calendar values and offsets are readable while times remain intact", () => {
  const text = readableAnswer(
    "16-Oct-2026 (2026-10-16), 11:35; 2026-10-10T12:00:00+03:00 [email_id=1]",
    "en",
  );
  expect(text).toContain("16 October 2026");
  expect(text).toContain("11:35");
  expect(text).not.toMatch(/email_id|2026-10|T12:/);
});

test("application-composed digest and status prose keeps all supported content", () => {
  const answer = {
    ...supported,
    answer_mode: "extractive" as const,
    answer:
      "During 1 October 2026 to 15 October 2026:\n" +
      "Your application was accepted, subject to identity verification. [email_id=11]\n" +
      "Upload your ID before Friday unless you already submitted it. [email_id=11]\n" +
      "This does not confirm your travel booking.",
  };
  const displayed = conversationalAnswer(
    answer,
    answer.sources,
    "en",
    true,
    "What changed recently?",
  );
  expect(displayed).toBe(answer.answer.replaceAll(" [email_id=11]", ""));
});
