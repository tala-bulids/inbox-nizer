import { DesktopTopBar } from "../../components/ui/DesktopTopBar";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { useLocale } from "../../app/locale";
import { RetroWindow } from "../../components/ui/RetroWindow";

export function OAuthComplete() {
  const { t, toggle, language } = useLocale();
  const [params] = useSearchParams();
  const result = params.get("result");
  const title =
    result === "success"
      ? t("انتهت خطوة اتصال Google", "Google connection step completed")
      : result === "denied"
        ? t("لم تمنح الموافقة", "Consent was not granted")
        : result === "expired"
          ? t("انتهت صلاحية محاولة الاتصال", "Connection attempt expired")
          : t("تعذر إكمال الاتصال", "Connection could not be completed");
  const isSuccess = result === "success";

  return (
    <div className="public-desktop">
      <DesktopTopBar
        language={language === "ar" ? "ar" : "en"}
        onToggleLanguage={toggle}
      />
      <main className="login public-window">
        <RetroWindow
          title={t("ربط حساب Google", "Google Account Connection")}
          icon={
            isSuccess ? (
              <CheckCircle2 size={16} className="text-[#81B29A]" />
            ) : (
              <AlertCircle size={16} className="text-[#E07A5F]" />
            )
          }
        >
          <div className="p-6 flex flex-col items-center text-center gap-4">
            <div
              className={`w-12 h-12 rounded-[3px] border-[1.5px] border-[#241E18] flex items-center justify-center shadow-[2px_2px_0px_#241E18] ${isSuccess ? "bg-[#EBF2EE] text-[#2D5A43]" : "bg-[#FBE8E4] text-[#B8422A]"}`}
            >
              {isSuccess ? (
                <CheckCircle2 size={24} />
              ) : (
                <AlertCircle size={24} />
              )}
            </div>
            <h1 className="text-lg font-bold">{title}</h1>
            <p className="text-xs text-[#241E18]/70">
              {result === "success"
                ? t(
                    "افتح الإعدادات للتحقق من حالة حساب Gmail.",
                    "Open Settings to verify your Gmail account status.",
                  )
                : t(
                    "يمكنك بدء محاولة اتصال جديدة من الإعدادات.",
                    "Start a fresh connection attempt in Settings.",
                  )}
            </p>
            <Link className="button primary" to="/settings">
              {t("الانتقال إلى الإعدادات", "Go to Settings")}
            </Link>
            <p className="muted text-xs">
              {t(
                "إذا فتح Google تبويبًا جديدًا، يمكنك أيضًا العودة إلى تبويب التطبيق وتحديث الحالة.",
                "If Google opened a new tab, you can also return to the app tab and refresh status.",
              )}
            </p>
          </div>
        </RetroWindow>
      </main>
    </div>
  );
}
