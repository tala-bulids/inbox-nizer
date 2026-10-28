import { z } from "zod";

export const Email = z.object({
  id: z.number(),
  subject: z.string(),
  body: z.string(),
  date: z.string(),
  language: z.string(),
  sender: z.string(),
});
export type CollectionEmail = z.infer<typeof Email>;
export const Collection = z.object({
  provenance: z.string(),
  emails: z.array(Email),
});
export const Analysis = z.object({
  predictions: z.array(
    z.object({ category: z.string(), confidence: z.number() }),
  ),
  summary: z.string(),
  classifier_status: z.string(),
  summary_method: z.string(),
});
export const Tasks = z.object({
  method: z.string(),
  tasks: z.array(
    z.object({
      email_id: z.number(),
      task: z.string(),
      confidence: z.number(),
      deadline_text: z.string().nullable(),
      deadline_date: z.string().nullable(),
      evidence: z.object({ subject: z.string(), body: z.string() }),
    }),
  ),
});
export const Answer = z.object({
  status: z.string(),
  answer: z.string(),
  mode: z.string(),
  verification: z.string(),
  sources: z.array(
    z.object({
      email_id: z.number(),
      subject: z.string(),
      content: z.string(),
      score: z.number(),
    }),
  ),
});
export const Lab = z.object({
  checkpoint: z.string(),
  weight_sha256: z.string(),
  provenance: z.string(),
  quality: z.string(),
  evidence_date: z.string(),
  methodology: z.string(),
  inference: z.string(),
  languages: z.record(
    z.string(),
    z.object({ n: z.number(), correct: z.number() }),
  ),
  development: z.object({
    n: z.number(),
    top1_accuracy: z.number(),
    top1_macro_f1: z.number(),
  }),
});

export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  signal: AbortSignal,
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api/showcase/${path}`, {
    method: body === undefined ? "GET" : "POST",
    credentials: "omit",
    cache: "no-store",
    signal,
    ...(body === undefined
      ? {}
      : {
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
  });
  if (!response.ok)
    throw new Error(
      response.status === 429
        ? "busy"
        : response.status === 503
          ? "model"
          : "request",
    );
  return schema.parse(await response.json());
}
