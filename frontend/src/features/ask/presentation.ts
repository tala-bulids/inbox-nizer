import type { AskAnswer } from "../../api/ask";

const locale = (language: string) =>
  language === "ar" ? "ar-SA-u-ca-gregory" : "en-GB";
const iso =
  /\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?\b/g;

export function readableDate(value: string, language: string): string | null {
  // Parse only explicit calendar dates/timestamps or standard email headers.
  if (
    !/^(?:\d{4}-\d{2}-\d{2}(?:T|$)|(?:[A-Za-z]{3},?\s+)?\d{1,2}[-\s][A-Za-z]{3,9}[-\s]\d{4})/.test(
      value,
    )
  ) {
    return null;
  }
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return null;
  const hasTime = /^\d{4}-\d{2}-\d{2}T/.test(value);
  return new Intl.DateTimeFormat(locale(language), {
    day: "numeric",
    month: "long",
    year: "numeric",
    ...(hasTime ? { hour: "numeric", minute: "2-digit" } : { timeZone: "UTC" }),
  }).format(date);
}

export function readableAnswer(value: string, language: string): string {
  return value
    .replace(/\[email_id=\d+\]/g, "")
    .replace(
      iso,
      (date) =>
        readableDate(date, language) ??
        (language === "ar" ? "تاريخ غير متاح" : "date unavailable"),
    )
    .replace(
      /\b\d{1,2}-[A-Za-z]{3}-\d{4}\b/g,
      (date) => readableDate(date, language) ?? date,
    )
    .replace(/[ \t]+\n/g, "\n")
    .trim();
}

function displayName(sender: string): string {
  // A display name is metadata, not proof of an organization or platform.
  const name = sender
    .replace(/<[^>]*>/g, "")
    .replace(/^["']|["']$/g, "")
    .trim();
  return name.includes("@") ? "" : name;
}

export function conversationalAnswer(
  answer: AskAnswer,
  sources: AskAnswer["sources"],
  language: string,
  supported: boolean,
  question = "",
): string {
  const raw = answer.answer;
  const clean = readableAnswer(raw, language);
  // Only compress the application's known metadata/excerpt wrapper. Never infer
  // facts from generated prose or translate/shorten a conditional source sentence.
  if (
    !supported ||
    answer.answer_mode !== "extractive" ||
    !/^(?:رسائل مرتبطة بسؤالك|Messages supporting your question)/.test(raw)
  )
    return clean;
  const ar = language === "ar";
  const count = new Intl.NumberFormat(locale(language)).format(sources.length);
  const existence = /(?:وجدت رسالة من |Found an email from )/.test(raw);
  const details =
    /(?:تفاصيل|بالتفصيل|كل رسالة|details|each email|each message)/i.test(
      question,
    );
  if (!sources.length) return clean;
  const period = raw.match(
    /\((\d{4}-\d{2}-\d{2}) – (\d{4}-\d{2}-\d{2}) \(UTC\)\)/,
  );
  const scope = period
    ? (ar ? " خلال الفترة من " : " between ") +
      readableDate(period[1]!, language) +
      (ar ? " إلى " : " and ") +
      readableDate(period[2]!, language)
    : "";
  if (existence && !details) {
    const names = [...new Set(sources.map((s) => displayName(s.from || "")))];
    const sender =
      names.length === 1 && names[0] ? (ar ? " من " : " from ") + names[0] : "";
    const intro = ar
      ? sources.length === 1
        ? `نعم، وجدت رسالة${sender} تطابق سؤالك${scope}.`
        : `نعم، وجدت ${count} رسائل${sender} تطابق سؤالك${scope}.`
      : `Yes, I found ${count} matching ${sources.length === 1 ? "email" : "emails"}${sender}${scope}.`;
    // Only claim the newest returned match when every returned date is known.
    const dated = sources.map((s) => ({
      value: s.date,
      formatted: readableDate(s.date, language),
    }));
    if (dated.every((d) => d.formatted)) {
      dated.sort((a, b) => Date.parse(b.value) - Date.parse(a.value));
      return (
        intro +
        (ar
          ? " أحدث هذه الرسائل وصلت بتاريخ "
          : " The latest of these arrived on ") +
        dated[0]!.formatted +
        "."
      );
    }
    return intro;
  }
  const intro = ar
    ? `وجدت لك ${count} رسائل مرتبطة بسؤالك${scope}.`
    : `I found ${count} messages relevant to your question${scope}.`;
  // Preserve supported actions, conditions and negation. Titles alone cannot
  // substitute for an answer to a digest or multi-email question.
  const lines = raw.split(/\n/).map((line) =>
    line
      .replace(/^.*? — (?:مقتطفات من البريد|email excerpts):\s*/, "")
      .replace(/^- \d{4}-\d{2}-\d{2}T\S+: /, "")
      .replace(/^- (?:تاريخ غير متاح|date unavailable): /, ""),
  );
  return intro + "\n\n" + readableAnswer(lines.join("\n"), language);
}
