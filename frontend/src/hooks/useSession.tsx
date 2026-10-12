/* eslint-disable react-refresh/only-export-components -- Provider and hook share one private context. */
import { createContext, useContext } from "react";
import type { PropsWithChildren } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { User } from "@/types/api";

interface Session {
  user: User | undefined;
  loading: boolean;
  setupRequired: boolean;
  requiresSetupToken: boolean;
  unavailable: boolean;
  refresh: () => void;
  authenticate: (username: string, password: string, setupToken?: string) => Promise<void>;
  logout: () => Promise<void>;
}
const SessionContext = createContext<Session | null>(null);
export function SessionProvider({ children }: PropsWithChildren) {
  const cache = useQueryClient();
  const status = useQuery({
    queryKey: ["auth-status"],
    queryFn: async () =>
      (
        await apiClient.get<{ setup_required: boolean; requires_setup_token: boolean }>(
          "/auth/status"
        )
      ).data,
    retry: 1,
  });
  const session = useQuery({
    queryKey: ["session"],
    queryFn: async () => (await apiClient.get<User>("/auth/me")).data,
    enabled: status.data?.setup_required === false,
    retry: false,
  });
  const value: Session = {
    user: session.data ?? undefined,
    loading: status.isPending || (status.data?.setup_required === false && session.isPending),
    setupRequired: status.data?.setup_required ?? false,
    requiresSetupToken: status.data?.requires_setup_token ?? false,
    unavailable: status.isError,
    refresh: () => {
      void status.refetch();
      void session.refetch();
    },
    authenticate: async (username, password, setupToken) => {
      const { data } = await apiClient.post<User>(
        status.data?.setup_required ? "/auth/setup" : "/auth/login",
        { username, password },
        { headers: setupToken ? { "X-Nimbus-Setup-Token": setupToken } : {} }
      );
      cache.setQueryData(["session"], data);
      cache.setQueryData(["auth-status"], { setup_required: false, requires_setup_token: false });
    },
    logout: async () => {
      await apiClient.post("/auth/logout");
      cache.setQueryData(["session"], null);
      cache.removeQueries({
        predicate: (query) => !["session", "auth-status"].includes(String(query.queryKey[0])),
      });
    },
  };
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("Session provider is required.");
  return value;
}
