import { DesktopTopBar } from "../components/ui/DesktopTopBar";
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
import { ApiClient, ApiError } from "../api/client";
import { accounts } from "../api/accounts";
import type { Accounts } from "../api/contracts";
import { createQueryClient, keys } from "../app/query";
import { useLocale } from "../app/locale";
import { Loading, ErrorState } from "../components/shared/States";
import { KeyRound } from "lucide-react";
import { RetroWindow } from "../components/ui/RetroWindow";
type Auth = {
  api: ApiClient;
  demo?: boolean;
  getAccessToken: () => string | undefined;
  getCurrentUser: () => {
    kind: "operator-token" | "browser-session" | "demo";
    profileAvailable: false;
  };
  logout: () => void;
};
export const AuthContext = createContext<Auth | null>(null);
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider required");
  return value;
}
function Session({
  token,
  csrf,
  initial,
  logout,
  children,
}: {
  token?: string;
  csrf?: string;
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
    () =>
      new ApiClient(
        () => token,
        logout,
        undefined,
        () => csrf,
      ),
    [token, csrf, logout],
  );
  useEffect(
    () => () => {
      api.dispose();
      queryClient.clear();
    },
    [api, queryClient],
  );
  return (
    <AuthContext.Provider
      value={{
        api,
        getAccessToken: () => token,
        getCurrentUser: () => ({
          kind: token ? "operator-token" : "browser-session",
          profileAvailable: false,
        }),
        logout,
      }}
    >
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </AuthContext.Provider>
  );
}
type LoginSession = { token?: string; csrf?: string; initial: Accounts };
function readCsrf(value: unknown): string {
  if (
    !value ||
    typeof value !== "object" ||
    !("csrf_token" in value) ||
    typeof value.csrf_token !== "string" ||
    !/^[a-f0-9]{64}$/.test(value.csrf_token)
  )
    throw new Error("Invalid browser session");
  return value.csrf_token;
}
export function AuthProvider({ children }: { children: ReactNode }) {
  const { t, toggle, language } = useLocale();
  const browserMode =
    !import.meta.env.DEV || import.meta.env.VITE_AUTH_MODE === "browser";
  const [session, setSession] = useState<LoginSession | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<unknown>();
  const [logoutCsrf, setLogoutCsrf] = useState<string>();
  const expire = useCallback(() => {
    setSession(null);
    setInput("");
  }, []);
  useEffect(() => {
    const api = new ApiClient(
      () => undefined,
      () => {},
    );
    let alive = true;
    void (async () => {
      try {
        const csrf = readCsrf(await api.request("/auth/session"));
        const initial = await accounts.list(api);
        if (alive) setSession({ csrf, initial });
      } catch (e) {
        if (alive && !(e instanceof ApiError && e.code === 401)) setError(e);
      } finally {
        api.dispose();
        if (alive) setChecking(false);
      }
    })();
    return () => {
      alive = false;
      api.dispose();
    };
  }, [browserMode]);
  async function googleLogin() {
    if (busy) return;
    setBusy(true);
    setError(undefined);
    const api = new ApiClient(
      () => undefined,
      () => {},
    );
    try {
      const url = await accounts.signIn(api);
      window.location.assign(url);
    } catch (e) {
      setError(e);
      setBusy(false);
    } finally {
      api.dispose();
    }
  }
  async function login() {
    if (busy || !input.trim()) return;
    setBusy(true);
    setError(undefined);
    const token = input.trim();
    setInput("");
    const api = new ApiClient(
      () => token,
      () => {},
    );
    try {
      if (browserMode) {
        const csrf = readCsrf(
          await api.request("/auth/session", { method: "POST" }),
        );
        const cookieApi = new ApiClient(
          () => undefined,
          () => {},
        );
        try {
          const initial = await accounts.list(cookieApi);
          setSession({ csrf, initial });
          setLogoutCsrf(undefined);
        } finally {
          cookieApi.dispose();
        }
      } else {
        setSession({ token, initial: await accounts.list(api) });
      }
    } catch (e) {
      setError(e);
    } finally {
      api.dispose();
      setBusy(false);
    }
  }
  async function endSession() {
    const csrf = session?.csrf || logoutCsrf;
    expire();
    if (!csrf) return;
    setLogoutCsrf(csrf);
    setBusy(true);
    const api = new ApiClient(
      () => undefined,
      () => {},
      undefined,
      () => csrf,
    );
    try {
      await api.request("/auth/session", { method: "DELETE" });
      setLogoutCsrf(undefined);
      setError(undefined);
    } catch (e) {
      setError(e);
    } finally {
      api.dispose();
      setBusy(false);
    }
  }
  if (checking)
    return (
      <main className="login">
        <Loading />
      </main>
    );
  if (session)
    return (
      <Session
        token={session.token}
        csrf={session.csrf}
        initial={session.initial}
        logout={expire}
      >
        <LogoutContext.Provider value={endSession}>
          {children}
        </LogoutContext.Provider>
      </Session>
    );
  return (
    <div className="public-desktop">
      <DesktopTopBar
        language={language === "ar" ? "ar" : "en"}
        onToggleLanguage={toggle}
      />
      <main className="login public-window">
        <RetroWindow
          title={t("تسجيل الدخول", "Sign In")}
          subtitle="inbox-nizer"
          icon={<KeyRound size={16} className="text-[#E07A5F]" />}
        >
          <div className="p-6 flex flex-col gap-4">
            <div className="flex items-center gap-3 p-3 bg-[#FAF6EE] border border-[#241E18]/20 rounded-[3px]">
              <div className="brand-mark m-0">✦</div>
              <div>
                <p className="product-name" dir="ltr">
                  inbox-nizer
                </p>
                <h1 className="text-base font-bold m-0">
                  {t(
                    "أهلاً بك في صندوقك الوارد المرتب",
                    "Welcome to your organized inbox",
                  )}
                </h1>
              </div>
            </div>
            <button
              className="primary"
              disabled={busy}
              onClick={() => void googleLogin()}
            >
              {t("المتابعة باستخدام Google", "Continue with Google")}
            </button>
            {new URLSearchParams(window.location.search).has("login") && (
              <p role="alert">
                {t(
                  "لم يكتمل تسجيل الدخول. أعد المحاولة أو تواصل مع المسؤول للتأكد من السماح لحسابك.",
                  "Sign-in was not completed. Retry or ask your administrator to confirm account access.",
                )}
              </p>
            )}
            {import.meta.env.DEV && (
              <details open>
                <summary>{t("دخول تطويري", "Development sign-in")}</summary>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void login();
                  }}
                  className="flex flex-col gap-3 my-1"
                >
                  <label htmlFor="token">
                    {browserMode
                      ? t("رمز الدخول", "Access code")
                      : t("رمز الوصول التطويري", "Development access token")}
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
              </details>
            )}
            {logoutCsrf && (
              <div role="alert">
                <p>
                  {t(
                    "لم يتأكد إنهاء جلسة الخادم. أعد محاولة تسجيل الخروج قبل ترك الجهاز.",
                    "Server sign-out is not confirmed. Retry before leaving this device.",
                  )}
                </p>
                <button disabled={busy} onClick={() => void endSession()}>
                  {t("إعادة تسجيل الخروج", "Retry sign-out")}
                </button>
              </div>
            )}
            {error !== undefined && <ErrorState error={error} />}
          </div>
        </RetroWindow>
      </main>
    </div>
  );
}
const LogoutContext = createContext<(() => Promise<void>) | null>(null);
export function useSignOut() {
  const browserLogout = useContext(LogoutContext);
  const { logout } = useAuth();
  return browserLogout || logout;
}
