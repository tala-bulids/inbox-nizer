import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthProvider";
import { useLocale } from "../../app/locale";
import { keys } from "../../app/query";
import { emails } from "../../api/emails";
import { Loading, Empty, ErrorState } from "../../components/shared/States";
export function SearchPage() {
  const { api } = useAuth();
  const { t } = useLocale();
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const query = useQuery({
    queryKey: keys.search(search),
    queryFn: ({ signal }) => emails.search(api, search, signal),
    enabled: !!search,
    staleTime: 60_000,
    retry: false,
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">DISCOVER</p>
          <h1>{t("ابحث بالمعنى", "Search by meaning")}</h1>
          <p>
            {t(
              "اعثر على الرسالة، حتى لو لم تتذكر كلماتها. هذا بحث عن البريد وليس إجابة مولّدة.",
              "Find the email, even without its exact words. Discovery, not generated answers.",
            )}
          </p>
        </div>
      </div>
      <form
        className="search-form"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(input.trim());
        }}
      >
        <label htmlFor="search">
          {t("ما الذي تبحث عنه؟", "What are you looking for?")}
        </label>
        <div className="input-row">
          <input
            id="search"
            dir="auto"
            maxLength={4000}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t(
              "رسالة عن موعد رحلتي…",
              "An email about my travel date…",
            )}
          />
          <button className="primary" disabled={!input.trim()}>
            {t("بحث", "Search")}
          </button>
        </div>
      </form>
      {!search ? (
        <Empty
          title={t("ابدأ بوصف ما تتذكره", "Start with what you remember")}
        />
      ) : query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      ) : !query.data.results.length ? (
        <Empty title={t("لا توجد نتائج", "No results")} />
      ) : (
        <ul className="result-list">
          {query.data.results.map((item) => (
            <li key={item.email.id}>
              <Link to={`/email/${item.email.id}`}>
                <h2 dir="auto">
                  {item.email.subject || t("بلا عنوان", "No subject")}
                </h2>
                <p className="muted" dir="auto">
                  {item.email.from}
                </p>
                <p className="preview" dir="auto">
                  {item.matched_text}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
