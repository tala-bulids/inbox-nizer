// Runtime adapters only for routes whose live OpenAPI response schema is empty.
// Source of truth: email_serialization.py, routes.py and account_routes.py.
import { z } from "zod";
import { ApiError } from "./client";
const text = z
  .string()
  .nullish()
  .transform((v) => v || "");
export const taskSchema = z.object({
  task: text,
  deadline_text: text,
  deadline_date: text,
  deadline_at: text,
});
export const emailSchema = z.object({
  id: z.number().int().positive(),
  message_id: text,
  from: text,
  date: text,
  sent_at: text,
  message_at: text,
  subject: text,
  summary: text,
  priority_level: text,
  created_at: text,
  body: text,
  predictions: z.array(z.object({ category: text })).default([]),
  tasks: z.array(taskSchema).default([]),
  processing: z.array(z.object({ status: text })).default([]),
});
export type Email = z.infer<typeof emailSchema>;
export const inboxSchema = z.object({
  count: z.number(),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  emails: z.array(emailSchema),
});
export const searchSchema = z.object({
  count: z.number(),
  query: z.string(),
  results: z.array(
    z.object({
      email: emailSchema.pick({
        sent_at: true,
        message_at: true,
        date: true,
        id: true,
        from: true,
        subject: true,
        summary: true,
        priority_level: true,
      }),
      matched_text: text,
    }),
  ),
});
export type SearchResult = z.infer<typeof searchSchema>["results"][number];
export const accountsSchema = z.object({
  accounts: z.array(
    z.object({
      id: z.number(),
      address: z.string(),
      status: z.string(),
      last_synced_at: text,
      sync_error: text,
      sync_pending: z.boolean().optional(),
      initial_sync_pending: z.boolean().optional(),
      message_count: z.number().optional(),
    }),
  ),
  sync_interval_seconds: z.number().optional(),
});
export type Accounts = z.infer<typeof accountsSchema>;
export const oauthSchema = z.object({ authorization_url: z.string().url() });
export const syncSchema = z.object({
  count: z.number(),
  success_count: z.number(),
  failed_count: z.number(),
  enrichment_failed: z.number(),
  has_more: z.boolean().optional(),
  progress_token: z.string().optional(),
});
export function parse<T>(schema: z.ZodType<T>, value: unknown): T {
  const result = schema.safeParse(value);
  if (!result.success) throw new ApiError("contract");
  return result.data;
}
