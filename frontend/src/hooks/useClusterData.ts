import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import type { Job, Summary, Worker } from "@/types/api";

export function useLiveUpdates() {
  const cache = useQueryClient();
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    let closed = false;
    let socket: WebSocket | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const configured = import.meta.env.VITE_WS_BASE_URL;
    const base =
      (configured?.startsWith("/")
        ? `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}${configured}`
        : configured) ??
      `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/v1`;
    const connect = () => {
      if (closed) return;
      socket = new WebSocket(`${base}/ws`);
      socket.onopen = () => {
        setConnected(true);
        void cache.invalidateQueries();
      };
      socket.onmessage = () => {
        ["workers", "jobs", "job", "summary", "logs", "artifacts"].forEach((key) => {
          void cache.invalidateQueries({ queryKey: [key] });
        });
      };
      socket.onclose = () => {
        setConnected(false);
        if (!closed) timer = setTimeout(connect, 3000);
      };
      socket.onerror = () => socket?.close();
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, [cache]);
  return connected;
}

export function useClusterData() {
  const workers = useQuery({
    queryKey: ["workers"],
    queryFn: async () => (await apiClient.get<Worker[]>("/workers")).data,
    refetchInterval: 10_000,
  });
  const jobs = useQuery({
    queryKey: ["jobs", "recent"],
    queryFn: async () => (await apiClient.get<Job[]>("/jobs", { params: { limit: 8 } })).data,
    refetchInterval: 10_000,
  });
  const summary = useQuery({
    queryKey: ["summary"],
    queryFn: async () => (await apiClient.get<Summary>("/jobs/summary")).data,
    refetchInterval: 10_000,
  });
  return {
    workers: workers.data ?? [],
    jobs: jobs.data ?? [],
    summary: summary.data,
    loading: workers.isPending || jobs.isPending || summary.isPending,
    error: workers.error ?? jobs.error ?? summary.error,
  };
}
