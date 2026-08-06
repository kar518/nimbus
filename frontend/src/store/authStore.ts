import { create } from "zustand";

interface AuthState {
  token: string | null;
  setToken: (token: string | null) => void;
  clear: () => void;
}

/**
 * Minimal auth store shell. No login/refresh flow is wired up yet —
 * this exists so `api/client.ts` and future auth pages have a single,
 * typed place to read/write the current session token.
 */
export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  setToken: (token) => set({ token }),
  clear: () => set({ token: null }),
}));
