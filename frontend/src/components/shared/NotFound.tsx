import { Link } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { useLocale } from "../../app/locale";
import { RetroWindow } from "../ui/RetroWindow";

export function NotFound() {
  const { t } = useLocale();
  return (
    <div className="max-w-md mx-auto my-12">
      <RetroWindow
        title={t("صفحة غير موجودة", "Page not found")}
        icon={<AlertCircle size={16} className="text-[#E07A5F]" />}
      >
        <section className="state p-6 flex flex-col items-center text-center">
          <p className="eyebrow">404</p>
          <h1>{t("الصفحة غير موجودة", "Page not found")}</h1>
          <p>
            {t(
              "تحقق من الرابط أو عد إلى بريدك.",
              "Check the link or return to your inbox.",
            )}
          </p>
          <Link className="button" to="/">
            {t("العودة إلى البريد الوارد", "Back to inbox")}
          </Link>
        </section>
      </RetroWindow>
    </div>
  );
}
