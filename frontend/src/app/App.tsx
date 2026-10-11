import { lazy } from "react";
import { AppBoundary } from "../components/shared/AppBoundary";
import { NotFound } from "../components/shared/NotFound";
import { OAuthComplete } from "../features/settings/OAuthComplete";
import { Routes, Route, useLocation } from "react-router-dom";
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
import { AuthProvider } from "../auth/AuthProvider";
import { LocaleProvider } from "./locale";
import { SearchSession } from "../features/search/SearchSession";
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
                <Routes>
                  <Route element={<Shell />}>
                    <Route index element={<InboxPage />} />
                    <Route path="email/:id" element={<EmailPage />} />
                    <Route path="search" element={<SearchPage />} />
                    <Route path="ask" element={<AskPage />} />
                    <Route path="tasks" element={<TasksPage />} />
                    <Route path="settings" element={<SettingsPage />} />
                    <Route path="*" element={<NotFound />} />
                  </Route>
                </Routes>
              </SearchSession>
            </AuthProvider>
          </>
        )}
      </AppBoundary>
    </LocaleProvider>
  );
}
