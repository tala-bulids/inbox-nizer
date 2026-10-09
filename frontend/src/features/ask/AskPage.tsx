import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { ask, validId, type AskRequest } from "../../api/ask";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Loading, ErrorState, Empty } from "../../components/shared/States";
import { AnswerView } from "./AnswerView";
import { AskComposer } from "./AskComposer";
export function AskPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const [question, setQuestion] = useState("");
  const controller = useRef<AbortController | null>(null);
  const locked = useRef(false);
  useEffect(
    () => () => {
      controller.current?.abort();
    },
    [],
  );
  const mutation = useMutation({
    retry: false,
    mutationFn: async (body: AskRequest) => {
      const active = new AbortController();
      controller.current = active;
      try {
        return await ask(api, body, active.signal);
      } finally {
        locked.current = false;
      }
    },
  });
  function submit(body: AskRequest) {
    if (
      locked.current ||
      !body.question.trim() ||
      body.question.length > 2000 ||
      (body.email_id != null && !validId(body.email_id))
    )
      return;
    locked.current = true;
    mutation.mutate(body);
  }
  return (
    <div className="ask-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">ASK YOUR INBOX</p>
          <h1>{t("إجابات تبدأ من بريدك", "Answers start with your email")}</h1>
          <p>
            {t(
              "اسأل عن موعد أو طلب. سنوضح ما يدعمه البريد وما هو نص مولّد.",
              "Ask about a date or application. See what your email supports and what is generated.",
            )}
          </p>
        </div>
      </div>
      <AskComposer
        draft={question}
        onChange={setQuestion}
        busy={mutation.isPending}
        onSubmit={() => submit({ question: question.trim() })}
      />
      {mutation.variables && (
        <div className="asked-question">
          <small>{t("السؤال المُرسل", "Submitted question")}</small>
          <p dir="auto">{mutation.variables.question}</p>
          {mutation.variables.email_id && (
            <small>
              {t(
                "تم اختيار رسالة للإجابة عن هذا السؤال.",
                "An email was selected for this question.",
              )}
            </small>
          )}
        </div>
      )}
      <div
        role="region"
        aria-label={t("نتيجة السؤال", "Question result")}
        aria-live="polite"
        aria-busy={mutation.isPending}
      >
        {mutation.isPending ? (
          <Loading />
        ) : mutation.isError ? (
          <ErrorState
            error={mutation.error}
            retry={() => mutation.variables && submit(mutation.variables)}
          />
        ) : mutation.data ? (
          <AnswerView
            answer={mutation.data}
            onClarify={(id) =>
              submit({ question: mutation.variables.question, email_id: id })
            }
          />
        ) : (
          <Empty
            title={t("ما الذي تريد معرفته؟", "What would you like to know?")}
            detail={t(
              "قد نطلب منك اختيار رسالة عندما توجد عدة إجابات محتملة.",
              "We may ask you to select an email when several answers are possible.",
            )}
          />
        )}
      </div>
    </div>
  );
}
