import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ask, type AskRequest } from "../../api/ask";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Loading, ErrorState, Empty } from "../../components/shared/States";
import { AnswerView } from "./AnswerView";
export function AskPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const [question, setQuestion] = useState("");
  const mutation = useMutation({
    mutationFn: (body: AskRequest) => ask(api, body),
  });
  return (
    <div className="ask-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">ASK YOUR INBOX</p>
          <h1>{t("إجابات تبدأ من بريدك", "Answers start with your email")}</h1>
          <p>
            {t(
              "اسأل عن موعد أو طلب. وسنوضح ما يدعمه المصدر وما ولّده الذكاء الاصطناعي.",
              "Ask about a date or application. Source support and generated prose stay distinct.",
            )}
          </p>
        </div>
      </div>
      <form
        className="surface ask-form"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate({ question: question.trim() });
        }}
      >
        <label htmlFor="question">{t("سؤالك", "Your question")}</label>
        <textarea
          id="question"
          dir="auto"
          rows={3}
          maxLength={2000}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("متى موعد رحلتي؟", "When is my trip?")}
        />
        <div className="form-footer">
          <small>
            {t(
              "من بريدك فقط. راجع المصدر عند الحاجة.",
              "Your email only. Review the source when needed.",
            )}
          </small>
          <button
            className="primary"
            disabled={!question.trim() || mutation.isPending}
          >
            {t("اسأل البريد", "Ask AI")}
          </button>
        </div>
      </form>
      <div aria-live="polite" aria-busy={mutation.isPending}>
        {mutation.isPending ? (
          <Loading />
        ) : mutation.isError ? (
          <ErrorState
            error={mutation.error}
            retry={() =>
              mutation.variables && mutation.mutate(mutation.variables)
            }
          />
        ) : mutation.data ? (
          <>
            <p className="asked-question" dir="auto">
              {mutation.variables.question}
            </p>
            <AnswerView
              answer={mutation.data}
              onClarify={(id) =>
                mutation.mutate({
                  question: mutation.variables.question,
                  email_id: id,
                })
              }
            />
          </>
        ) : (
          <Empty
            title={t("ما الذي تريد معرفته؟", "What would you like to know?")}
            detail={t(
              "قد نطلب منك تحديد البريد إذا وُجدت عدة إجابات محتملة.",
              "We may ask you to choose an email when several answers are possible.",
            )}
          />
        )}
      </div>
    </div>
  );
}
