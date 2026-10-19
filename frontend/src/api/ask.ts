import type { components } from "./generated/schema";
import type { ApiClient } from "./client";
import { ApiError } from "./client";
export type AskAnswer = components["schemas"]["AnswerResponse"];
export type AskRequest = components["schemas"]["QuestionRequest"];
// Generated types define the response. Fail closed on malformed states at runtime.
export async function ask(
  api: ApiClient,
  body: AskRequest,
  signal?: AbortSignal,
): Promise<AskAnswer> {
  const value = await api.request("/ask", { method: "POST", body, signal });
  if (
    !value ||
    typeof value !== "object" ||
    !("answer" in value) ||
    typeof value.answer !== "string" ||
    !("status" in value) ||
    !["answered", "needs_clarification", "insufficient_evidence"].includes(
      String(value.status),
    ) ||
    !("sources" in value) ||
    !Array.isArray(value.sources) ||
    !("citations" in value) ||
    !Array.isArray(value.citations) ||
    !value.sources.every(
      (source) =>
        !source ||
        !validId(source.email_id) ||
        (typeof source.subject === "string" &&
          typeof source.from === "string" &&
          typeof source.date === "string"),
    ) ||
    ("clarification_options" in value &&
      value.clarification_options != null &&
      !Array.isArray(value.clarification_options))
  )
    throw new ApiError("contract");
  // IDs are checked again before links or follow-up requests. Valid source IDs
  // require textual metadata so malformed responses cannot break presentation.
  return value as AskAnswer;
}
export function validId(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}
