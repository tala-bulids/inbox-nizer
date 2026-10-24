import type { AskAnswer } from "../api/ask";
export const email = {
  id: 11,
  message_id: "fake-message",
  from: "team@example.invalid",
  subject: "مواعيد مؤتمر المعرفة",
  date: "8 Oct 2026",
  summary: "ملخص آلي تجريبي للرسالة",
  priority_level: "high",
  created_at: "2026-10-08",
  body: "Original message: reference SAMPLE42. Departure 11:35. <script>unsafe</script>",
  predictions: [{ category: "Events", confidence: 0.8 }],
  tasks: [
    {
      task: "تأكيد الحضور",
      confidence: 0.8,
      deadline_text: "12 October",
      deadline_date: "2026-10-12",
      deadline_at: null,
      deadline_confidence: 0.8,
    },
  ],
};
export const inbox = {
  count: 1,
  total: 1,
  limit: 20,
  offset: 0,
  emails: [email],
};
export const accountData = {
  accounts: [
    {
      id: 2,
      address: "demo@example.invalid",
      status: "connected",
      last_synced_at: new Date().toISOString(),
      sync_error: null,
    },
  ],
};
export const supported: AskAnswer = {
  status: "answered",
  answer: "12 October [email_id=11]",
  answer_mode: "extractive",
  verification: "source_supported",
  sources: [
    {
      email_id: 11,
      chunk_id: 4,
      chunk_index: 0,
      score: 0.8,
      subject: email.subject,
      from: email.from,
      date: email.date,
    },
  ],
  citations: [{ email_id: 11 }],
};
export const generated: AskAnswer = {
  ...supported,
  answer:
    "Generated synthesis, not a semantically verified extraction. Review the original email.\n\nThey will contact you. [email_id=11]",
  answer_mode: "generated_synthesis",
  verification: "not_semantically_verified",
};
export const clarification: AskAnswer = {
  status: "needs_clarification",
  answer: "حدد الطلب المقصود",
  sources: [],
  citations: [],
  clarification_options: [
    { email_id: 11, subject: "طلب الجهة الأولى", date: "8 Oct 2026" },
    { email_id: 12, subject: "طلب الجهة الثانية", date: "9 Oct 2026" },
  ],
};

export const taskPage = {
  count: 2,
  total: 2,
  limit: 20,
  offset: 0,
  tasks: [
    {
      id: 101,
      task: "إرسال المستند Submit document",
      deadline_text: "قبل الموعد",
      deadline_date: "2026-10-12",
      deadline_at: null,
      created_at: "2026-10-01T10:00:00Z",
      email: {
        id: 11,
        subject: "طلب مستندات Documents",
        sender: "team@example.invalid",
        date: "8 Oct 2026",
        sent_at: "2026-10-08T10:00:00Z",
        message_at: null,
      },
    },
    {
      id: 102,
      task: "الرد على الرسالة",
      deadline_text: null,
      deadline_date: null,
      deadline_at: null,
      created_at: "2026-10-01T10:00:00Z",
      email: {
        id: 12,
        subject: null,
        sender: null,
        date: null,
        sent_at: null,
        message_at: null,
      },
    },
  ],
};
