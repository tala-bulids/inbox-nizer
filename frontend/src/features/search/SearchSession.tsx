import { createContext, useContext, useState, type ReactNode } from "react";
const Context = createContext<{
  draft: string;
  submitted: string;
  setDraft: (value: string) => void;
  setSubmitted: (value: string) => void;
} | null>(null);
// Mounted inside AuthProvider: private search state dies with the session.
export function SearchSession({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState("");
  const [submitted, setSubmitted] = useState("");
  return (
    <Context.Provider value={{ draft, submitted, setDraft, setSubmitted }}>
      {children}
    </Context.Provider>
  );
}
export function useSearchSession() {
  const value = useContext(Context);
  if (!value) throw new Error("SearchSession required");
  return value;
}
