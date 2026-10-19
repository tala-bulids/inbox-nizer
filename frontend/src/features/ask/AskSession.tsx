import { createContext, useContext, useState, type ReactNode } from "react";
import type { AskAnswer, AskRequest } from "../../api/ask";
type Result = { answer: AskAnswer; request: AskRequest };
const Context = createContext<{
  history: string[];
  remember: (value: string) => void;
  question: string;
  setQuestion: (value: string) => void;
  result: Result | undefined;
  setResult: (value: Result | undefined) => void;
} | null>(null);
// Private state is discarded with the authenticated session.
export function AskSession({ children }: { children: ReactNode }) {
  const [history, setHistory] = useState<string[]>([]);
  const remember = (value: string) =>
    setHistory((old) => [...old, value].slice(-4));
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<Result>();
  return (
    <Context.Provider
      value={{ question, setQuestion, result, setResult, history, remember }}
    >
      {children}
    </Context.Provider>
  );
}
export function useAskSession() {
  const value = useContext(Context);
  if (!value) throw new Error("AskSession required");
  return value;
}
