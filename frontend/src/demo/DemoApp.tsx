import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { Routes, Route, Link } from "react-router-dom";
import { AuthContext } from "../auth/AuthProvider";
import { createQueryClient, keys } from "../app/query";
import { LocaleProvider, useLocale } from "../app/locale";
import { AppBoundary } from "../components/shared/AppBoundary";
import { NotFound } from "../components/shared/NotFound";
import { Shell } from "../components/layout/Shell";
import { InboxPage } from "../features/inbox/InboxPage";
import { EmailPage } from "../features/email/EmailPage";
import { TasksPage } from "../features/tasks/TasksPage";
import { RetroWindow } from "../components/ui/RetroWindow";
import { DemoClient } from "./DemoClient";
import { demoAccounts } from "./fixtures";
function DemoSettings() {
  const { t } = useLocale();
  return (
    <RetroWindow title={t("عن العرض", "About the demo")}>
      <section className="p-6 flex flex-col gap-4">
        <h1>{t("استكشف Inbox-nizer", "Explore Inbox-nizer")}</h1>
        <p>
          {t(
            "جرّب تصفية البريد حسب التصنيف والأولوية، افتح الرسائل، وراجع ملخصات ومهام الأمثلة. لا يعمل أي نموذج ذكاء اصطناعي في هذا العرض.",
            "Filter the inbox by category and priority, open messages, and explore example summaries and source-linked tasks. No AI model runs in this demo.",
          )}
        </p>
        <Link to="/">{t("جرّب العرض", "Try Demo")}</Link>
        <h2>{t("Gmail غير متصل", "Gmail is not connected")}</h2>
        <p>
          {t(
            "الاتصال والمزامنة وإعادة المعالجة غير متاحة في العرض. التطبيق الخاص يتطلب مستخدماً مصرحاً وموافقة Gmail منفصلة. جاهزية الإنتاج الكاملة غير معتمدة.",
            "Connection, synchronization and reprocessing are unavailable in the demo. The private app requires an authorized user and separate Gmail consent. Full production readiness is not approved.",
          )}
        </p>
        <button disabled>
          {t(
            "ربط Gmail غير متاح في العرض",
            "Connect Gmail unavailable in demo",
          )}
        </button>
        <p>
          {t(
            "لا تُطلب بيانات دخول، ولا تُقرأ ملفات جلسات، ولا يوجد اتصال بقاعدة بيانات. جميع عناوين الرسائل خيالية.",
            "No sign-in is requested, session credentials are not read, and no database is contacted. All message addresses are fictional.",
          )}
        </p>
        <a
          href="https://github.com/tala-bulids/inbox-nizer"
          target="_blank"
          rel="noreferrer"
        >
          {t("الكود والتوثيق", "Source code & documentation")}
        </a>
      </section>
    </RetroWindow>
  );
}
export function DemoApp() {
  const [api] = useState(() => new DemoClient());
  const [client] = useState(() => {
    const q = createQueryClient();
    q.setQueryData(keys.accounts, demoAccounts);
    return q;
  });
  return (
    <LocaleProvider>
      <AppBoundary>
        <AuthContext.Provider
          value={{
            api,
            demo: true,
            getAccessToken: () => undefined,
            getCurrentUser: () => ({ kind: "demo", profileAvailable: false }),
            logout: () => {},
          }}
        >
          <QueryClientProvider client={client}>
            <Routes>
              <Route element={<Shell demo />}>
                <Route index element={<InboxPage />} />
                <Route path="email/:id" element={<EmailPage />} />
                <Route path="tasks" element={<TasksPage />} />
                <Route path="settings" element={<DemoSettings />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </QueryClientProvider>
        </AuthContext.Provider>
      </AppBoundary>
    </LocaleProvider>
  );
}
