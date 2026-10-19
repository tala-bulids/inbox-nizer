import { lazy } from "react";
import { AppBoundary } from "../components/shared/AppBoundary";
import { NotFound } from "../components/shared/NotFound";
import { OAuthComplete } from "../features/settings/OAuthComplete";
import { Routes, Route, useLocation, Navigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { accounts } from "../api/accounts";
import { keys } from "./query";
import { Shell } from "../components/layout/Shell";
const InboxPage = lazy(() =>
  import("../features/inbox/InboxPage").then((m) => ({ default: m.InboxPage })),
);
const EmailPage = lazy(() =>
  import("../features/email/EmailPage").then((m) => ({ default: m.EmailPage })),
);
const SearchPage = lazy(() =>
  import("../features/search/SearchPage").then((m) => ({
    default: m.SearchPage,
  })),
);
const AskPage = lazy(() =>
  import("../features/ask/AskPage").then((m) => ({ default: m.AskPage })),
);
const TasksPage = lazy(() =>
  import("../features/tasks/TasksPage").then((m) => ({ default: m.TasksPage })),
);
const SettingsPage = lazy(() =>
  import("../features/settings/SettingsPage").then((m) => ({
    default: m.SettingsPage,
  })),
);
import { AuthProvider, useAuth } from "../auth/AuthProvider";
import { LocaleProvider } from "./locale";
import { AskSession } from "../features/ask/AskSession";
import { SearchSession } from "../features/search/SearchSession";
function InboxEntry() {
  const { api } = useAuth();
  const { data } = useQuery({
    queryKey: keys.accounts,
    queryFn: ({ signal }) => accounts.list(api, signal),
  });
  // The authenticated session seeds this query. Keep the decision reactive so
  // connecting Gmail and refreshing Settings immediately unlocks the Inbox.
  if (data && data.accounts.length === 0)
    return <Navigate to="/settings" replace />;
  return <InboxPage />;
}
export function App() {
  const location = useLocation();
  return (
    <LocaleProvider>
      <AppBoundary>
        {location.pathname === "/oauth/complete" ? (
          <OAuthComplete />
        ) : (
          <>
            <AuthProvider>
              <SearchSession>
                <AskSession>
                  <Routes>
                    <Route element={<Shell />}>
                      <Route index element={<InboxEntry />} />
                      <Route path="email/:id" element={<EmailPage />} />
                      <Route path="search" element={<SearchPage />} />
                      <Route path="ask" element={<AskPage />} />
                      <Route path="tasks" element={<TasksPage />} />
                      <Route path="settings" element={<SettingsPage />} />
                      <Route path="*" element={<NotFound />} />
                    </Route>
                  </Routes>
                </AskSession>
              </SearchSession>
            </AuthProvider>
          </>
        )}
      </AppBoundary>
    </LocaleProvider>
  );
}
