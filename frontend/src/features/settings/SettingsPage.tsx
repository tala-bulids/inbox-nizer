import { useEffect, useRef, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  useIsMutating,
} from "@tanstack/react-query";
import { Settings } from "lucide-react";
import { accounts, syncAll, type SyncProgress } from "../../api/accounts";
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
  const qc = useQueryClient();
  const syncLock = useRef(false);
  const syncController = useRef<AbortController | null>(null);
  const [progress, setProgress] = useState<SyncProgress | null>(null);
  useEffect(() => () => syncController.current?.abort(), []);
  const connectLock = useRef(false);
  const syncing = useIsMutating({ mutationKey: ["gmail-sync"] }) > 0;
  const connecting = useIsMutating({ mutationKey: ["gmail-connect"] }) > 0;
  const query = useQuery({
    queryKey: keys.accounts,
    queryFn: ({ signal }) => accounts.list(api, signal),
  });
  const sync = useMutation({
    mutationKey: ["gmail-sync"],
    retry: false,
    mutationFn: (id: number) => {
      const controller = new AbortController();
      syncController.current = controller;
      return syncAll(api, id, controller.signal, setProgress);
    },
    onSettled: async () => {
      try {
        await qc.cancelQueries({ queryKey: ["search"] });
        qc.removeQueries({ queryKey: ["search"] });
        await Promise.all([
          qc.invalidateQueries({ queryKey: keys.accounts }),
          qc.invalidateQueries({ queryKey: keys.emails }),
          qc.invalidateQueries({ queryKey: keys.tasks }),
        ]);
      } finally {
        syncLock.current = false;
      }
    },
  });
  const connect = useMutation({
    mutationKey: ["gmail-connect"],
    retry: false,
    mutationFn: () => accounts.connect(api),
    onSettled: () => {
      connectLock.current = false;
    },
  });
  function startSync(id: number) {
    if (syncLock.current || syncing) return;
    syncLock.current = true;
    setProgress(null);
    sync.mutate(id);
  }
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
              <button
                disabled={query.isFetching}
                onClick={() => void query.refetch()}
              >
                {t("تحديث الحالة", "Refresh status")}
              </button>
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
                    {t("آخر مزامنة: ", "Last sync: ")}
                    {account.last_synced_at ? (
                      <EmailDate value={account.last_synced_at} />
                    ) : (
                      t("لم تتم المزامنة بعد", "Not synced yet")
                    )}
                  </p>
                  {account.sync_error && (
                    <p className="muted">
                      {t(
                        "لم تكتمل المزامنة الأخيرة. حاول مجددًا أو أعد الاتصال.",
                        "The last sync did not finish. Retry or reconnect.",
                      )}
                    </p>
                  )}
                  <div className="account-actions">
                    <button
                      disabled={syncing || account.status !== "connected"}
                      onClick={() => startSync(account.id)}
                    >
                      {syncing && sync.variables === account.id
                        ? t("جارٍ المزامنة…", "Syncing…")
                        : t("مزامنة Gmail", "Sync Gmail")}
                    </button>
                    <button
                      disabled={connecting || syncing}
                      onClick={startConnect}
                    >
                      {t("إعادة الاتصال", "Reconnect")}
                    </button>
                  </div>
                  {account.sync_pending && !syncing && (
                    <p className="muted">
                      {t(
                        "يوجد تقدم محفوظ. مزامنة Gmail تستكمل من حيث توقفت.",
                        "Progress is saved. Sync Gmail resumes where it stopped.",
                      )}
                    </p>
                  )}
                </article>
              ))
            ) : (
              <Empty title={t("لا يوجد حساب متصل", "No connected account")} />
            )}
            {syncing && (
              <p role="status">
                {t("جارٍ مزامنة البريد…", "Syncing email…")}{" "}
                {t("تمت مزامنة", "Synced")} {progress?.success_count ?? 0}{" "}
                {t("رسالة.", "messages.")}
              </p>
            )}
            {sync.isError && (
              <>
                <ErrorState error={sync.error} />
                <p role="status">
                  {t("توقفت المزامنة. تمت مزامنة", "Sync stopped. Synced")}{" "}
                  {progress?.success_count ?? 0}{" "}
                  {t(
                    "رسالة في هذه المحاولة. التقدم المحفوظ لن يُحذف. تحقق من الاتصال ثم حاول مجددًا؛ إذا طُلب إعادة ربط Gmail فاستخدم إعادة الاتصال.",
                    "messages in this run. Saved progress is retained. Check the connection and retry; reconnect Gmail if requested.",
                  )}
                </p>
              </>
            )}
            {sync.data && !syncing && (
              <p role="status" className="sync-result">
                {sync.data.reason === "complete"
                  ? t(
                      "اكتملت المزامنة بنجاح. تمت مزامنة",
                      "Sync completed successfully. Synced",
                    )
                  : t(
                      "توقفت المزامنة مؤقتًا. تمت مزامنة",
                      "Sync paused. Synced",
                    )}{" "}
                {sync.data.success_count} {t("رسالة.", "messages.")}{" "}
                {t(
                  "رسائل تعذرت معالجتها: ",
                  "Messages that could not be processed: ",
                )}
                {sync.data.failed_count}.{" "}
                {t(
                  "معلومات مساعدة غير مكتملة: ",
                  "Incomplete derived information: ",
                )}
                {sync.data.enrichment_failed}.
                {sync.data.reason !== "complete" &&
                  t(
                    " تم حفظ التقدم. توقفت المتابعة التلقائية بسبب خطأ أو عدم تقدم أو بلوغ حد الأمان. حاول مزامنة Gmail لاحقًا للاستكمال.",
                    " Progress saved. Automatic sync stopped after an error, no progress, or the safety limit. Sync Gmail later to resume.",
                  )}
              </p>
            )}
          </section>
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
              {t("اتصال Gmail أو إعادة الاتصال", "Connect or reconnect Gmail")}
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
                    "بعد الموافقة ستعود إلى صفحة نتيجة الاتصال في التطبيق. افتح الإعدادات للتحقق من الحساب، أو عد إلى هذا التبويب وحدّث الحالة. الرابط صالح لعشر دقائق.",
                    "After consent, the app shows the connection result. Open Settings to verify the account, or return to this tab and refresh status. The link is valid for ten minutes.",
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
