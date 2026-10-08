import { ApiError } from "../../api/client";
import { useLocale } from "../../app/locale";
export function Loading() {
  const { t } = useLocale();
  return (
    <div role="status" className="state">
      <p>{t("جارٍ التحميل…", "Loading…")}</p>
      {[1, 2, 3].map((n) => (
        <div className="skeleton" key={n} />
      ))}
    </div>
  );
}
export function Empty({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="state">
      <h2>{title}</h2>
      {detail && <p>{detail}</p>}
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  const { t } = useLocale();
  const code = error instanceof ApiError ? error.code : 0;
  const messages: Record<string, [string, string]> = {
    401: [
      "انتهت الجلسة. سجّل الدخول مجددًا.",
      "Session expired. Sign in again.",
    ],
    403: ["لا تملك صلاحية هذا الطلب.", "Access denied."],
    404: [
      "البريد غير موجود أو غير متاح لحسابك.",
      "Email not found or unavailable to your account.",
    ],
    409: [
      "توجد عملية جارية أو تعارض. حاول لاحقًا.",
      "An operation is already running or conflicts. Try later.",
    ],
    422: ["تحقق من البيانات المدخلة.", "Check the submitted values."],
    503: [
      "الخدمة غير متاحة الآن. حاول لاحقًا.",
      "Service unavailable. Try again later.",
    ],
    network: ["تعذر الاتصال بالخادم.", "Unable to reach the server."],
    contract: [
      "وصل رد غير متوقع من الخادم.",
      "The server returned an unexpected response.",
    ],
  };
  const message = messages[String(code)] || [
    "تعذر إكمال الطلب.",
    "Unable to complete the request.",
  ];
  return (
    <div role="alert" className="error">
      <p>{t(message[0]!, message[1]!)}</p>
      {retry && <button onClick={retry}>{t("إعادة المحاولة", "Retry")}</button>}
    </div>
  );
}
