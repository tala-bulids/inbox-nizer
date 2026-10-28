import { useLocale } from "../../app/locale";
export function AskComposer({
  draft,
  onChange,
  busy,
  onSubmit,
  maxLength = 2000,
}: {
  draft: string;
  onChange: (v: string) => void;
  busy: boolean;
  onSubmit: () => void;
  maxLength?: number;
}) {
  const { t } = useLocale();
  return (
    <form
      className="surface ask-form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <label htmlFor="question">{t("سؤالك", "Your question")}</label>
      <textarea
        id="question"
        dir="auto"
        rows={3}
        maxLength={maxLength}
        value={draft}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t("متى موعد رحلتي؟", "When is my trip?")}
        aria-describedby="ask-help"
        onKeyDown={(e) => {
          if (
            e.key === "Enter" &&
            (e.ctrlKey || e.metaKey) &&
            !e.nativeEvent.isComposing
          ) {
            e.preventDefault();
            onSubmit();
          }
        }}
      />
      <div className="form-footer">
        <small id="ask-help">
          {t(
            "كل سؤال مستقل. Enter لسطر جديد، Ctrl/⌘ + Enter للإرسال.",
            "Each question is independent. Enter for a new line; Ctrl/⌘ + Enter to submit.",
          )}
        </small>
        <button className="primary" disabled={busy || !draft.trim()}>
          {busy ? t("جارٍ الإجابة…", "Answering…") : t("اسأل البريد", "Ask AI")}
        </button>
      </div>
    </form>
  );
}
