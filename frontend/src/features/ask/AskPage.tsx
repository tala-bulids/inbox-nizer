import { useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { ask, validId, type AskRequest } from "../../api/ask";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Loading, ErrorState, Empty } from "../../components/shared/States";
import { AnswerView } from "./AnswerView";
import { AskComposer } from "./AskComposer";
import { RetroWindow } from "../../components/ui/RetroWindow";

import { useAskSession } from "./AskSession";

export function AskPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const { question, setQuestion, result, setResult, history, remember } =
    useAskSession();
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
    onSuccess: (answer, request) => {
      setResult({ answer, request });
      if (answer.status === "answered") remember(request.question);
    },
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
    setResult(undefined);
    mutation.mutate(body);
  }
  const answer =
    mutation.data ?? (mutation.isIdle ? result?.answer : undefined);
  const submitted = mutation.variables ?? result?.request;
  return (
    <div className="ask-page flex flex-col gap-4">
      <div className="page-heading">
        <div>
          <h1>{t("اسأل البريد", "Ask Mail")}</h1>
          <p>
            {t(
              "اسأل عن رسائلك ومواعيدك وآخر المستجدات.",
              "Ask about your messages, dates, and recent updates.",
            )}
          </p>
        </div>
      </div>
      <RetroWindow
        title={t("اسأل البريد", "Ask Mail")}
        icon={<Sparkles size={16} className="text-[#E07A5F]" />}
      >
        <div className="p-4 sm:p-6 flex flex-col gap-4">
          <AskComposer
            draft={question}
            onChange={setQuestion}
            busy={mutation.isPending}
            onSubmit={() =>
              submit({
                question: question.trim(),
                ...(history.length ? { history } : {}),
              })
            }
          />
          {submitted && (
            <div className="asked-question">
              <small>{t("السؤال المُرسل", "Submitted question")}</small>
              <p dir="auto">{submitted!.question}</p>
              {submitted.email_id && (
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
            ) : answer ? (
              <AnswerView
                answer={answer}
                question={submitted?.question}
                onClarify={(id) =>
                  submit({
                    question: submitted!.question,
                    email_id: id,
                    history: submitted?.history,
                  })
                }
              />
            ) : (
              <Empty
                title={t(
                  "ما الذي تريد معرفته؟",
                  "What would you like to know?",
                )}
                detail={t(
                  "قد نطلب منك اختيار رسالة عندما توجد عدة إجابات محتملة.",
                  "We may ask you to select an email when several answers are possible.",
                )}
              />
            )}
          </div>
        </div>
      </RetroWindow>
    </div>
  );
}
