import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { accounts } from "../../api/accounts";
import { keys } from "../../app/query";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { Loading, ErrorState, Empty } from "../../components/shared/States";
import { Identifier } from "../../components/ui/Text";
export function SettingsPage() {
  const { api, getCurrentUser } = useAuth();
  const { t } = useLocale();
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: keys.accounts,
    queryFn: ({ signal }) => accounts.list(api, signal),
  });
  const sync = useMutation({
    mutationFn: (id: number) => accounts.sync(api, id),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: keys.accounts });
      void qc.invalidateQueries({ queryKey: keys.emails });
      qc.removeQueries({ queryKey: ["search"] });
    },
  });
  const connect = useMutation({ mutationFn: () => accounts.connect(api) });
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">WORKSPACE SETTINGS</p>
          <h1>{t("الحساب والاتصال", "Account & connection")}</h1>
          <p>
            {t(
              "أدر اتصال Gmail والمزامنة من هنا.",
              "Manage Gmail connection and synchronization.",
            )}
          </p>
        </div>
      </div>
      <section className="surface settings-section">
        <h2>{t("جلسة التطبيق", "Application session")}</h2>
        <p>
          {t(
            "جلسة تطويرية برمز مشغّل. لا تتوفر واجهة ملف مستخدم حاليًا.",
            "Development operator-token session. A current-user profile endpoint is not available.",
          )}
        </p>
        <span className="badge">
          <Identifier>{getCurrentUser().kind}</Identifier>
        </span>
      </section>
      <section className="surface settings-section">
        <div className="section-heading">
          <h2>Gmail</h2>
          <button onClick={() => void query.refetch()}>
            {t("تحديث الحالة", "Refresh status")}
          </button>
        </div>
        {query.isPending ? (
          <Loading />
        ) : query.isError ? (
          <ErrorState error={query.error} />
        ) : query.data.accounts.length ? (
          query.data.accounts.map((account) => (
            <div className="account" key={account.id}>
              <h3>
                <Identifier>{account.address}</Identifier>
              </h3>
              <div className="tags">
                <span className="badge">{account.status}</span>
                <span>
                  {t("آخر مزامنة: ", "Last sync: ")}
                  <Identifier>{account.last_synced_at || "—"}</Identifier>
                </span>
              </div>
              {account.sync_error && (
                <p className="muted">
                  {t(
                    "لم تكتمل المزامنة الأخيرة. يمكنك المحاولة مجددًا.",
                    "The last sync did not finish. You can retry.",
                  )}
                </p>
              )}
              <button
                onClick={() => sync.mutate(account.id)}
                disabled={sync.isPending || account.status !== "connected"}
              >
                {sync.isPending
                  ? t("جارٍ المزامنة…", "Syncing…")
                  : t("مزامنة الآن", "Sync now")}
              </button>
            </div>
          ))
        ) : (
          <Empty title={t("لا يوجد حساب متصل", "No connected account")} />
        )}
        {sync.isError && <ErrorState error={sync.error} />}{" "}
        {sync.data && (
          <p role="status">
            {t("تمت معالجة", "Processed")} {sync.data.success_count} ·{" "}
            {t("إخفاقات", "Failures")}: {sync.data.failed_count} ·{" "}
            {t("إثراء غير مكتمل", "Enrichment incomplete")}:{" "}
            {sync.data.enrichment_failed}
          </p>
        )}
        <hr />
        <button
          className="primary"
          disabled={connect.isPending}
          onClick={() => connect.mutate()}
        >
          {t("اتصال Gmail أو إعادة الاتصال", "Connect or reconnect Gmail")}
        </button>
        {connect.isError && <ErrorState error={connect.error} />}{" "}
        {connect.data && (
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
                "أكمل الاتصال في النافذة الجديدة، ثم عد واضغط تحديث الحالة. ينتهي الرابط خلال عشر دقائق.",
                "Finish in the new tab, then return and refresh status. This link expires in ten minutes.",
              )}
            </p>
          </div>
        )}
      </section>
    </>
  );
}
