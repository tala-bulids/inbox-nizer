import { useRef } from "react";
import { useMutation, useQuery, useIsMutating } from "@tanstack/react-query";
import { Settings } from "lucide-react";
import { accounts } from "../../api/accounts";
import { useGmailSync } from "./GmailSync";
import { keys } from "../../app/query";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Loading, ErrorState, Empty } from "../../components/shared/States";
import { Identifier } from "../../components/ui/Text";
import { EmailDate } from "../../components/ui/EmailDate";
import { RetroWindow } from "../../components/ui/RetroWindow";

export function SettingsPage() {
  const { api, getCurrentUser } = useAuth();
  const { t } = useLocale();
  const { states, update } = useGmailSync();
  const connectLock = useRef(false);
  const syncing = Object.values(states).some(
    (state) => state.phase === "running",
  );
  const connecting = useIsMutating({ mutationKey: ["gmail-connect"] }) > 0;
  const query = useQuery({
    queryKey: keys.accounts,
    queryFn: ({ signal }) => accounts.list(api, signal),
  });
  const connect = useMutation({
    mutationKey: ["gmail-connect"],
    retry: false,
    mutationFn: () => accounts.connect(api),
    onSettled: () => {
      connectLock.current = false;
    },
  });
  function startConnect() {
    if (connectLock.current || connecting) return;
    connectLock.current = true;
    connect.mutate();
  }
  function status(value: string) {
    return value === "connected"
      ? t("متصل", "Connected")
      : value === "disconnected"
        ? t("غير متصل", "Disconnected")
        : value === "reconnect_required"
          ? t("يلزم إعادة الاتصال", "Reconnect required")
          : t("الاتصال غير متاح", "Connection unavailable");
  }
  return (
    <div className="settings-page flex flex-col gap-4">
      <div className="page-heading">
        <div>
          <h1>{t("الحساب والاتصال", "Account & connection")}</h1>
          <p>
            {t(
              "تابع اتصال Gmail والمزامنة من هنا.",
              "Manage your Gmail connection and sync.",
            )}
          </p>
        </div>
      </div>
      <RetroWindow
        title={t("الإعدادات", "Settings")}
        icon={<Settings size={16} className="text-[#E07A5F]" />}
        subtitle={t("إعدادات Gmail والحساب", "Gmail & Account Settings")}
      >
        <div className="p-4 sm:p-6 flex flex-col gap-6">
          <section className="surface settings-section">
            <div className="section-heading">
              <h2>{t("حسابات Gmail", "Gmail accounts")}</h2>
            </div>
            {query.isPending ? (
              <Loading />
            ) : query.isError ? (
              <ErrorState
                error={query.error}
                retry={() => void query.refetch()}
              />
            ) : query.data.accounts.length ? (
              query.data.accounts.map((account) => (
                <article className="account" key={account.id}>
                  <h3>
                    <Identifier>{account.address}</Identifier>
                  </h3>
                  <p className="account-status">{status(account.status)}</p>
                  <p className="muted">
                    {t("آخر تحديث: ", "Last update: ")}
                    {account.last_synced_at ? (
                      <EmailDate value={account.last_synced_at} />
                    ) : (
                      t("جاري تجهيز البريد", "Preparing your inbox")
                    )}
                  </p>
                  {account.sync_error && (
                    <p className="muted">
                      {t(
                        "تعذر تحديث البريد مؤقتًا. سنحاول لاحقًا.",
                        "Mail could not be updated temporarily. We will try again later.",
                      )}
                    </p>
                  )}
                  <div className="account-actions">
                    {!!account.enrichment_failed_count && (
                      <p role="status">
                        {t(
                          "مزامنة Gmail منفصلة عن المعالجة المساعدة. رسائل تحتاج إعادة معالجة من صفحة التفاصيل:",
                          "Gmail sync is separate from enrichment. Open email details to retry failed derived information:",
                        )}{" "}
                        {account.enrichment_failed_count}
                      </p>
                    )}
                    <button
                      disabled={syncing || account.status !== "connected"}
                      onClick={() => update(account.id)}
                    >
                      {states[account.id]?.phase === "running"
                        ? t("جاري التحديث...", "Updating…")
                        : t("تحديث الآن", "Update now")}
                    </button>
                    {account.status !== "connected" && (
                      <button
                        disabled={connecting || syncing}
                        onClick={startConnect}
                      >
                        {t("إعادة الاتصال", "Reconnect")}
                      </button>
                    )}
                  </div>
                  {states[account.id]?.phase === "complete" && (
                    <p role="status" className="muted">
                      {t("تم تحديث البريد", "Mail updated")}
                    </p>
                  )}
                  {["paused", "error"].includes(
                    states[account.id]?.phase ?? "",
                  ) && (
                    <p role="status" className="muted">
                      {t(
                        "تعذر إكمال التحديث الآن. التقدم محفوظ وسنحاول تلقائيًا لاحقًا.",
                        "The update could not finish now. Progress is saved and we will retry automatically later.",
                      )}
                    </p>
                  )}
                </article>
              ))
            ) : (
              <Empty title={t("لا يوجد حساب متصل", "No connected account")} />
            )}
          </section>
          {(!query.data?.accounts.length ||
            query.data.accounts.some((a) => a.status !== "connected")) && (
            <section className="surface settings-section">
              <h2>{t("اتصال Gmail", "Gmail connection")}</h2>
              <p className="muted">
                {t(
                  "سيُفتح Google في تبويب جديد. لإعادة الاتصال، اختر عنوان Gmail نفسه هناك.",
                  "Google opens in a new tab. To reconnect, choose the same Gmail address there.",
                )}
              </p>
              <button
                className="primary"
                disabled={connecting || syncing}
                onClick={startConnect}
              >
                {t(
                  "اتصال Gmail أو إعادة الاتصال",
                  "Connect or reconnect Gmail",
                )}
              </button>
              {connecting && (
                <p role="status">
                  {t("جارٍ تجهيز الاتصال…", "Preparing connection…")}
                </p>
              )}
              {connect.isError && <ErrorState error={connect.error} />}
              {connect.data && !connecting && (
                <div className="oauth-ready">
                  <a
                    className="button"
                    href={connect.data}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {t("متابعة إلى Google", "Continue to Google")}
                  </a>
                  <p>
                    {t(
                      "بعد الموافقة سنفتح بريدك ونبدأ تجهيزه تلقائيًا.",
                      "After consent, your inbox opens and starts preparing automatically.",
                    )}
                  </p>
                  {import.meta.env.DEV && (
                    <small>
                      {t(
                        "استخدم localhost للواجهة والخادم معًا أثناء التطوير.",
                        "Use localhost for both frontend and backend during development.",
                      )}
                    </small>
                  )}
                </div>
              )}
            </section>
          )}
          <section className="development-note">
            {getCurrentUser().kind === "browser-session" ? (
              <>
                <h2>{t("جلسة متصفح آمنة", "Secure browser session")}</h2>
                <p>
                  {t(
                    "جلسة قصيرة تنتهي عند تسجيل الخروج أو انتهاء صلاحيتها. اتصال Gmail منفصل.",
                    "A short-lived session ends on sign-out or expiry. Gmail consent is separate.",
                  )}
                </p>
              </>
            ) : (
              <>
                <h2>{t("جلسة تطوير محلية", "Local development session")}</h2>
                <p>
                  {t(
                    "رمز دخول التطبيق يبقى في الذاكرة ويُحذف عند تحديث الصفحة أو الخروج. اتصال Gmail منفصل عن دخول التطبيق.",
                    "The app access token stays in memory and clears on reload or logout. Gmail consent is separate from app sign-in.",
                  )}
                </p>
              </>
            )}
          </section>
        </div>
      </RetroWindow>
    </div>
  );
}
