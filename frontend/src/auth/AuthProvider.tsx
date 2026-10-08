import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { ApiClient } from "../api/client";
import { accounts } from "../api/accounts";
import type { Accounts } from "../api/contracts";
import { createQueryClient, keys } from "../app/query";
import { useLocale } from "../app/locale";
import { ErrorState } from "../components/shared/States";
type Auth = {
  api: ApiClient;
  getAccessToken: () => string | undefined;
  getCurrentUser: () => { kind: "operator-token"; profileAvailable: false };
  logout: () => void;
};
const Context = createContext<Auth | null>(null);
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthProvider required");
  return value;
}
function Session({
  token,
  initial,
  logout,
  children,
}: {
  token: string;
  initial: Accounts;
  logout: () => void;
  children: ReactNode;
}) {
  const [queryClient] = useState(() => {
    const client = createQueryClient();
    client.setQueryData(keys.accounts, initial);
    return client;
  });
  const api = useMemo(
    () => new ApiClient(() => token, logout),
    [token, logout],
  );
  useEffect(
    () => () => {
      api.dispose();
      queryClient.clear();
    },
    [api, queryClient],
  );
  return (
    <Context.Provider
      value={{
        api,
        getAccessToken: () => token,
        getCurrentUser: () => ({
          kind: "operator-token",
          profileAvailable: false,
        }),
        logout,
      }}
    >
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </Context.Provider>
  );
}
export function AuthProvider({ children }: { children: ReactNode }) {
  const { t } = useLocale();
  const [session, setSession] = useState<{
    token: string;
    initial: Accounts;
  } | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();
  const logout = useCallback(() => {
    setSession(null);
    setInput("");
  }, []);
  async function login() {
    setBusy(true);
    setError(undefined);
    const token = input.trim();
    setInput("");
    const api = new ApiClient(
      () => token,
      () => {},
    );
    try {
      const initial = await accounts.list(api);
      setSession({ token, initial });
    } catch (e) {
      setError(e);
    } finally {
      api.dispose();
      setBusy(false);
    }
  }
  if (session)
    return (
      <Session token={session.token} initial={session.initial} logout={logout}>
        {children}
      </Session>
    );
  return (
    <main className="login">
      <div className="brand-mark">✦</div>
      <p className="eyebrow">SMART INBOX</p>
      <h1>{t("مساحة أهدأ لبريدك", "A calmer space for your inbox")}</h1>
      <p>
        {t(
          "دخول تطويري محلي. رمز المشغّل يبقى في الذاكرة ويُحذف عند تحديث الصفحة أو تسجيل الخروج.",
          "Local development sign-in. The operator token stays in memory and is cleared on reload or logout.",
        )}
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void login();
        }}
      >
        <label htmlFor="token">
          {t("رمز الوصول التطويري", "Development access token")}
        </label>
        <input
          id="token"
          type="password"
          dir="ltr"
          autoComplete="off"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          required
          disabled={busy}
        />
        <button className="primary" disabled={busy || !input.trim()}>
          {busy
            ? t("جارٍ التحقق…", "Checking…")
            : t("فتح مساحة العمل", "Open workspace")}
        </button>
      </form>
      {error !== undefined && <ErrorState error={error} />}
      <small>
        {t(
          "هذا ليس تسجيل دخول إنتاجيًا أو اتصال Gmail.",
          "This is not production browser login or Gmail authorization.",
        )}
      </small>
    </main>
  );
}
