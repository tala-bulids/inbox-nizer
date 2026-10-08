import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";
const Context = createContext({
  language: "ar",
  toggle: () => {},
  t: (ar: string, en: string) => ar || en,
});
export function LocaleProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState("ar");
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  }, [language]);
  return (
    <Context.Provider
      value={{
        language,
        t: (ar, en) => (language === "ar" ? ar : en),
        toggle: () => setLanguage((v) => (v === "ar" ? "en" : "ar")),
      }}
    >
      {children}
    </Context.Provider>
  );
}
export const useLocale = () => useContext(Context);
