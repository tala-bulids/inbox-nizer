import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { keys } from "../../app/query";
import { emails } from "../../api/emails";
import { Loading, Empty, ErrorState } from "../../components/shared/States";
import { useSearchSession } from "./SearchSession";
import { SearchResults } from "./SearchResults";
import { RetroWindow } from "../../components/ui/RetroWindow";

export function SearchPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const { draft, submitted, setDraft, setSubmitted } = useSearchSession();
  const query = useQuery({
    queryKey: keys.search(submitted),
    queryFn: ({ signal }) => emails.search(api, submitted, signal),
    enabled: !!submitted,
    staleTime: Infinity,
    gcTime: Infinity,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: false,
  });
  return (
    <div className="search-page flex flex-col gap-4">
      <div className="page-heading">
        <div>
          <h1>{t("ابحث عن إيميلك", "Find your email")}</h1>
          <p>
            {t(
              "اعثر على إيميلك بكتابة معنى الإيميل أو الغرض منه.",
              "Find an email by describing its meaning or purpose.",
            )}
          </p>
        </div>
      </div>
      <RetroWindow
        title={t("ابحث عن إيميلك", "Find your email")}
        icon={<Search size={16} className="text-[#E07A5F]" />}
      >
        <div className="p-4 sm:p-6 flex flex-col gap-4">
          <form
            className="surface search-form search-composer p-4 sm:p-5"
            role="search"
            onSubmit={(e) => {
              e.preventDefault();
              const next = draft.trim();
              if (!next || next.length > 4000) return;
              if (next === submitted) {
                if (!query.isFetching) void query.refetch();
              } else setSubmitted(next);
            }}
          >
            <label htmlFor="search">
              {t("ما الذي تبحث عنه؟", "What are you looking for?")}
            </label>
            <div className="input-row">
              <input
                id="search"
                type="search"
                dir="auto"
                maxLength={4000}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder={t(
                  "رسالة عن موعد رحلة أو طلب…",
                  "An email about a trip or application…",
                )}
              />
              <button
                className="primary"
                disabled={
                  !draft.trim() ||
                  (query.isFetching && draft.trim() === submitted)
                }
              >
                {t("بحث", "Search")}
              </button>
            </div>
            <small className="block mt-2">
              {t("نعرض حتى 10 رسائل ذات صلة.", "Up to 10 relevant emails.")}
            </small>
          </form>
          {submitted && (
            <div className="submitted-search">
              <small>{t("نتائج البحث عن", "Results for")}</small>
              <p dir="auto">{submitted}</p>
            </div>
          )}
          <section
            aria-label={t("نتائج البحث", "Search results")}
            aria-live="polite"
            aria-busy={!!submitted && query.isFetching}
          >
            {!submitted ? (
              <Empty
                title={t("ابدأ بوصف ما تتذكره", "Start with what you remember")}
              />
            ) : query.isPending || query.isFetching ? (
              <Loading />
            ) : query.isError ? (
              <ErrorState
                error={query.error}
                retry={() => void query.refetch()}
              />
            ) : !query.data.results.length ? (
              <Empty
                title={t("لا توجد نتائج", "No results")}
                detail={t(
                  "جرّب وصفًا آخر أو أضف اسم الجهة التي تتذكرها.",
                  "Try a different description or an organization you remember.",
                )}
              />
            ) : (
              <>
                <p className="result-count">
                  {query.data.count} {t("نتائج ذات صلة", "relevant results")}
                </p>
                <SearchResults items={query.data.results} />
              </>
            )}
          </section>
        </div>
      </RetroWindow>
    </div>
  );
}
