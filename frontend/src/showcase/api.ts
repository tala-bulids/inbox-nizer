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
  metadata: z.object({ reference_datetime: z.string() }).optional(),
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
      responsible: z.string().nullable().optional(),
      deadline_state: z.enum(["explicit", "missing", "ambiguous"]).optional(),
      state: z.string().optional(),
      superseded_by: z.array(z.number()).optional(),
      conditional: z.boolean().optional(),
      evidence: z.object({
        subject: z.string(),
        body: z.string(),
        text: z.string().optional(),
      }),
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

export const Prediction = Analysis.extend({
  model_version: z.string(),
  artifact_sha256: z.string(),
  processing_ms: z.number(),
  cold_load_included: z.boolean(),
  score_semantics: z.string(),
});
const Scores = z.object({
  precision: z.number(),
  recall: z.number(),
  f1: z.number(),
  support: z.number(),
});
export const Portfolio = z.object({
  selected: z.string(),
  evidence_version: z.string(),
  models: z.array(
    z.object({
      id: z.string(),
      run: z.object({
        artifact_sha256: z.string().nullable(),
        training_executed: z.boolean(),
        benchmark: z.object({
          p95_ms: z.number(),
          process_peak_wset_mib: z.number(),
        }),
        identity: z.record(z.string(), z.unknown()),
      }),
      metrics: z.object({
        n: z.number(),
        top1_accuracy: z.number(),
        top1_macro_f1: z.number(),
        top1_weighted_f1: z.number(),
        per_class: z.record(z.string(), Scores),
        confusion_matrix: z.array(z.array(z.number())),
        confusion_note: z.string(),
        top1_ece: z.number(),
        wrong_confident_ge_080: z.number(),
        error_patterns: z.record(z.string(), z.number()),
      }),
      history: z.object({
        method: z.string(),
        train_unweighted_binary_log_loss: z.number().optional(),
        validation_unweighted_binary_log_loss: z.number().optional(),
      }),
    }),
  ),
  dataset: z.object({
    usable_rows: z.number(),
    seed: z.number(),
    groups: z.number(),
    near_duplicate_pairs: z.number(),
    source: z.object({
      repository: z.string(),
      revision: z.string(),
      license: z.string(),
    }),
    splits: z.record(z.string(), z.object({ rows: z.number() })),
    class_counts: z.record(z.string(), z.number()),
    language_counts: z.record(z.string(), z.number()),
  }),
  configuration: z.object({
    linear: z.record(z.string(), z.union([z.string(), z.number()])),
    tfidf: z.record(z.string(), z.number()),
  }),
  historical: z.object({
    development: z.object({
      n: z.number(),
      top1_accuracy: z.number(),
      top1_macro_f1: z.number(),
    }),
    languages: z.record(
      z.string(),
      z.object({ n: z.number(), correct: z.number() }),
    ),
  }),
  rag: z.object({
    memory_mib: z.number(),
    qa: z.object({
      n: z.number(),
      retrieval: z.object({ "recall@5": z.number() }),
    }),
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
          : response.status === 413 || response.status === 422
            ? "input"
            : "request",
    );
  return schema.parse(await response.json());
}
