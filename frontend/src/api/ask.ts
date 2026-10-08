import type { components } from "./generated/schema";
import type { ApiClient } from "./client";
import { ApiError } from "./client";
export type AskAnswer = components["schemas"]["AnswerResponse"];
export type AskRequest = components["schemas"]["QuestionRequest"];
// Generated types define the response. Fail closed on malformed states at runtime.
export async function ask(
  api: ApiClient,
  body: AskRequest,
): Promise<AskAnswer> {
  const value = await api.request("/ask", { method: "POST", body });
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
    !Array.isArray(value.citations)
  )
    throw new ApiError("contract");
  // Boundary checked below before any source IDs become links or follow-up requests.
  return value as AskAnswer;
}
export function validId(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}
