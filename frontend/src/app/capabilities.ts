import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../auth/AuthProvider";
import { accounts } from "../api/accounts";
import { keys } from "./query";

export function useRetrievalEnabled() {
  const { api } = useAuth();
  const { data } = useQuery({
    queryKey: keys.accounts,
    queryFn: ({ signal }) => accounts.list(api, signal),
  });
  return !!data && data.runtime_profile !== "render-free";
}
