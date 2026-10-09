import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { keys } from "../../app/query";
import { emails } from "../../api/emails";
import { Loading, Empty, ErrorState } from "../../components/shared/States";
import { useSearchSession } from "./SearchSession";
import { SearchResults } from "./SearchResults";
export function SearchPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const { draft, submitted, setDraft, setSubmitted } = useSearchSession();
  const query = useQuery({
    queryKey: keys.search(submitted),
    queryFn: ({ signal }) => emails.search(api, submitted, signal),
    enabled: !!submitted,
    staleTime: 60_000,
    refetchOnMount: false,
    refetchOnReconnect: false,
    retry: false,
  });
  return (
    <div className="search-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">FIND EMAILS</p>
          <h1>{t("ابحث بالمعنى", "Search by meaning")}</h1>
          <p>
            {t(
              "اعثر على الرسالة حتى لو لم تتذكر كلماتها. النتائج رسائل ذات صلة، وليست إجابة مولّدة.",
              "Find emails even without their exact words. Results are relevant messages, not generated answers.",
            )}
          </p>
        </div>
      </div>
      <form
        className="surface search-form search-composer"
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
              !draft.trim() || (query.isFetching && draft.trim() === submitted)
            }
          >
            {t("بحث", "Search")}
          </button>
        </div>
        <small>
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
          <ErrorState error={query.error} retry={() => void query.refetch()} />
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
  );
}
