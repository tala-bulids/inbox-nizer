import { Routes, Route, Link } from "react-router-dom";
import { Shell } from "../components/layout/Shell";
import { InboxPage } from "../features/inbox/InboxPage";
import { EmailPage } from "../features/email/EmailPage";
import { SearchPage } from "../features/search/SearchPage";
import { AskPage } from "../features/ask/AskPage";
import { TasksPage } from "../features/tasks/TasksPage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { AuthProvider } from "../auth/AuthProvider";
import { LocaleProvider } from "./locale";
export function App() {
  return (
    <LocaleProvider>
      <AuthProvider>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<InboxPage />} />
            <Route path="email/:id" element={<EmailPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="ask" element={<AskPage />} />
            <Route path="tasks" element={<TasksPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route
              path="*"
              element={
                <section>
                  <h1>404</h1>
                  <Link to="/">البريد الوارد / Inbox</Link>
                </section>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </LocaleProvider>
  );
}
