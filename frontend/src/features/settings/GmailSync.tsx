import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { accounts, syncAll } from "../../api/accounts";
import type { Accounts } from "../../api/contracts";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { keys } from "../../app/query";

type Account = Accounts["accounts"][number];
type State = {
  phase: "running" | "paused" | "error" | "complete";
  count: number;
  initial: boolean;
};
type SyncContext = {
  states: Record<number, State>;
  update: (id: number) => void;
};
const Context = createContext<SyncContext | null>(null);

export function useGmailSync() {
  const context = useContext(Context);
  if (!context) throw new Error("GmailSyncProvider required");
  return context;
}

// Lives for the authenticated app session, across all route changes. PostgreSQL
// owns progress; browser locks only prevent duplicate work between local tabs.
export function GmailSyncProvider({ children }: { children: ReactNode }) {
  const { api } = useAuth();
  const qc = useQueryClient();
  const [states, setStates] = useState<Record<number, State>>({});
  const active = useRef(new Map<number, AbortController>());
  const nextRun = useRef(new Map<number, number>());
  const failures = useRef(new Map<number, number>());
  const alive = useRef(true);
  const { data } = useQuery({
    queryKey: keys.accounts,
    queryFn: ({ signal }) => accounts.list(api, signal),
  });
  const interval =
    Math.max(60, Math.min(3600, data?.sync_interval_seconds ?? 300)) * 1000;

  const refresh = useCallback(async () => {
    await Promise.all(
      [keys.accounts, keys.emails, keys.tasks].map((queryKey) =>
        qc.invalidateQueries({ queryKey }),
      ),
    );
    await qc.cancelQueries({ queryKey: ["search"] });
    qc.removeQueries({ queryKey: ["search"] });
  }, [qc]);

  const run = useCallback(
    async (account: Account, manual = false) => {
      if (
        !alive.current ||
        account.status !== "connected" ||
        active.current.has(account.id)
      )
        return;
      if (!manual && Date.now() < (nextRun.current.get(account.id) ?? 0))
        return;
      const controller = new AbortController();
      active.current.set(account.id, controller);
      const initial = account.initial_sync_pending ?? !account.last_synced_at;
      let count = account.message_count ?? 0;
      const show = (phase: State["phase"]) => {
        if (alive.current)
          setStates((old) => ({
            ...old,
            [account.id]: { phase, count, initial },
          }));
      };
      const work = async () => {
        if (controller.signal.aborted) return;
        show("running");
        let refreshedAt = 0;
        const result = await syncAll(
          api,
          account.id,
          controller.signal,
          async (progress) => {
            if (Date.now() - refreshedAt >= 2000) {
              refreshedAt = Date.now();
              await refresh(); // Inbox/categories become usable as messages arrive.
            }
            // Replayed/updated source messages are successful too. Count stored
            // rows so recovery/history overlap cannot inflate the inbox total.
            count =
              qc
                .getQueryData<Accounts>(keys.accounts)
                ?.accounts.find((item) => item.id === account.id)
                ?.message_count ??
              (account.message_count ?? 0) + progress.success_count;
            show("running");
            if (document.visibilityState === "hidden") controller.abort();
          },
          manual,
        );
        if (result.reason === "complete") {
          failures.current.delete(account.id);
          nextRun.current.set(account.id, Date.now() + interval);
          show("complete");
        } else {
          const n =
            result.reason === "limit"
              ? 0
              : Math.min(5, (failures.current.get(account.id) ?? 0) + 1);
          failures.current.set(account.id, n);
          nextRun.current.set(
            account.id,
            n >= 5
              ? Infinity
              : Date.now() +
                  (result.reason === "limit"
                    ? 60_000
                    : Math.min(30 * 60_000, interval * 2 ** (n - 1))),
          );
          show("paused");
        }
      };
      try {
        if (navigator.locks?.request) {
          await navigator.locks.request(
            `inbox-nizer:gmail:${account.id}`,
            { ifAvailable: true },
            async (lock) => {
              if (lock) await work();
              else nextRun.current.set(account.id, Date.now() + interval);
            },
          );
        } else await work(); // Server advisory lock remains authoritative.
      } catch {
        const n = Math.min(5, (failures.current.get(account.id) ?? 0) + 1);
        failures.current.set(account.id, n);
        nextRun.current.set(
          account.id,
          controller.signal.aborted
            ? 0
            : n >= 5
              ? Infinity
              : Date.now() + Math.min(30 * 60_000, interval * 2 ** (n - 1)),
        );
        show(controller.signal.aborted ? "paused" : "error");
      } finally {
        active.current.delete(account.id);
        if (alive.current) await refresh();
      }
    },
    [api, interval, qc, refresh],
  );

  useEffect(() => {
    alive.current = true;
    const controllers = active.current;
    return () => {
      alive.current = false;
      for (const controller of controllers.values()) controller.abort();
    };
  }, []);

  useEffect(() => {
    let checking = false;
    let lastCheck = -Infinity;
    const check = async () => {
      if (
        !alive.current ||
        checking ||
        document.visibilityState === "hidden" ||
        Date.now() - lastCheck < 15_000
      )
        return;
      checking = true;
      const firstCheck = lastCheck === -Infinity;
      lastCheck = Date.now();
      try {
        const seeded = firstCheck
          ? qc.getQueryData<Accounts>(keys.accounts)
          : undefined;
        const latest =
          seeded ??
          (await qc.fetchQuery({
            queryKey: keys.accounts,
            queryFn: ({ signal }) => accounts.list(api, signal),
            staleTime: 0,
          }));
        if (!latest) return;
        for (const account of latest.accounts) {
          if (account.source_failed_count && !account.sync_pending) continue;
          const stale =
            !account.last_synced_at ||
            Date.now() - Date.parse(account.last_synced_at) >= interval;
          if (account.sync_pending || account.initial_sync_pending || stale)
            await run(account);
        }
      } catch {
        /* A later bounded check can recover; never loop on auth/network errors. */
      } finally {
        checking = false;
      }
    };
    const onFocus = () => {
      void check();
    };
    const timer = window.setInterval(onFocus, Math.min(interval, 60_000));
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    void check();
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, [api, interval, qc, run]);

  const update = (id: number) => {
    const account = qc
      .getQueryData<Accounts>(keys.accounts)
      ?.accounts.find((a) => a.id === id);
    if (account) void run(account, true);
  };
  return (
    <Context.Provider value={{ states, update }}>{children}</Context.Provider>
  );
}

export function GmailSyncNotice() {
  const { states } = useGmailSync();
  const { t } = useLocale();
  const preparing = Object.values(states).find(
    (s) => s.initial && s.phase !== "complete",
  );
  if (!preparing) return null;
  return (
    <p role="status" className="muted">
      {preparing.phase === "running"
        ? t("جاري تجهيز بريدك", "Preparing your inbox")
        : t(
            "التقدم محفوظ. راجع الإعدادات لإعادة المحاولة عند الحاجة.",
            "Progress is saved. Check Settings to retry if needed.",
          )}{" "}
      {t("تم تجهيز", "Prepared")} {preparing.count} {t("رسالة.", "messages.")}{" "}
      {t(
        "يمكنك استخدام Inbox-nizer بينما نكمل تجهيز الرسائل.",
        "You can use Inbox-nizer while we prepare your messages.",
      )}
    </p>
  );
}
