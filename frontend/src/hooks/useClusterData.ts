import { useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "@/api/client";
import type { Job, Worker } from "@/types/api";

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000/api/v1";
const RECONNECT_DELAY_MS = 3_000;

/**
 * Fetches the current workers + jobs from the backend, then keeps them
 * live by listening on the `/ws` WebSocket for worker heartbeat/status
 * events and job assignment/status events (see
 * `app.services.event_bus` / `app.services.ws_manager` on the backend).
 *
 * Any event just invalidates the two queries rather than trying to
 * patch the cache in place — the lists are small, so a refetch is cheap
 * and keeps this hook simple and correct even as new event types are
 * added on the backend.
 */
export function useClusterData() {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);

  const workersQuery = useQuery({
    queryKey: ["workers"],
    queryFn: async () => {
      const { data } = await apiClient.get<Worker[]>("/workers");
      return data;
    },
    refetchInterval: 30_000,
  });

  const jobsQuery = useQuery({
    queryKey: ["jobs"],
    queryFn: async () => {
      const { data } = await apiClient.get<Job[]>("/jobs");
      return data;
    },
    refetchInterval: 30_000,
  });

  useEffect(() => {
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (cancelled) return;

      const socket = new WebSocket(`${WS_BASE_URL}/ws`);
      socketRef.current = socket;

      socket.onmessage = () => {
        // Any live event (worker heartbeat/status, job assignment/status)
        // just triggers a refetch of both lists.
        queryClient.invalidateQueries({ queryKey: ["workers"] });
        queryClient.invalidateQueries({ queryKey: ["jobs"] });
      };

      socket.onclose = () => {
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [queryClient]);

  return {
    workers: workersQuery.data ?? [],
    jobs: jobsQuery.data ?? [],
    loading: workersQuery.isLoading || jobsQuery.isLoading,
  };
}
