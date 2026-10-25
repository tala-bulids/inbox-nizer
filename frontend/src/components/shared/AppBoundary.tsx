import { Component, type ReactNode } from "react";
import { useLocale } from "../../app/locale";
import { RetroWindow } from "../ui/RetroWindow";
function Recovery() {
  const { t } = useLocale();
  return (
    <main className="login public-window" role="alert">
      <RetroWindow title="inbox-nizer">
        <div className="state">
          <h1>{t("تعذر عرض الصفحة", "Unable to display this page")}</h1>
          <p>
            {t("أعد تحميل التطبيق للمحاولة مجددًا.", "Reload to try again.")}
          </p>
          <button onClick={() => window.location.reload()}>
            {t("إعادة التحميل", "Reload")}
          </button>
        </div>
      </RetroWindow>
    </main>
  );
}
export class AppBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? <Recovery /> : this.props.children;
  }
}
