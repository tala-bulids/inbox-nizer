import { useRef } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  useIsMutating,
} from "@tanstack/react-query";
import { accounts } from "../../api/accounts";
import { keys } from "../../app/query";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Loading, ErrorState, Empty } from "../../components/shared/States";
import { Identifier } from "../../components/ui/Text";
import { EmailDate } from "../../components/ui/EmailDate";
export function SettingsPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const qc = useQueryClient();
  const syncLock = useRef(false);
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
    mutationFn: (id: number) => accounts.sync(api, id),
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
    <div className="settings-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">GMAIL SETTINGS</p>
          <h1>{t("الحساب والاتصال", "Account & connection")}</h1>
          <p>
            {t(
              "تابع اتصال Gmail والمزامنة من هنا.",
              "Manage your Gmail connection and sync.",
            )}
          </p>
        </div>
      </div>
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
          <ErrorState error={query.error} retry={() => void query.refetch()} />
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
                    : t("مزامنة الآن", "Sync now")}
                </button>
                <button disabled={connecting || syncing} onClick={startConnect}>
                  {t("إعادة الاتصال", "Reconnect")}
                </button>
              </div>
            </article>
          ))
        ) : (
          <Empty title={t("لا يوجد حساب متصل", "No connected account")} />
        )}
        {syncing && (
          <p role="status">
            {t(
              "جارٍ مزامنة البريد. قد تستغرق العملية بعض الوقت.",
              "Syncing email. This may take a little time.",
            )}
          </p>
        )}
        {sync.isError && <ErrorState error={sync.error} />}
        {sync.data && !syncing && (
          <p role="status" className="sync-result">
            {t("تمت معالجة", "Processed")} {sync.data.success_count}{" "}
            {t("رسالة.", "messages.")}{" "}
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
                "بعد الموافقة ستظهر صفحة JSON لتأكيد الاتصال. عد إلى هذا التبويب واضغط تحديث الحالة. رابط الموافقة صالح لعشر دقائق.",
                "After consent, a JSON confirmation page appears. Return to this tab and refresh status. The consent link is valid for ten minutes.",
              )}
            </p>
            <small>
              {t(
                "استخدم localhost للواجهة والخادم معًا أثناء التطوير.",
                "Use localhost for both frontend and backend during development.",
              )}
            </small>
          </div>
        )}
      </section>
      <section className="development-note">
        <h2>{t("جلسة تطوير محلية", "Local development session")}</h2>
        <p>
          {t(
            "رمز دخول التطبيق يبقى في الذاكرة ويُحذف عند تحديث الصفحة أو الخروج. اتصال Gmail منفصل عن دخول التطبيق.",
            "The app access token stays in memory and clears on reload or logout. Gmail consent is separate from app sign-in.",
          )}
        </p>
      </section>
    </div>
  );
}
