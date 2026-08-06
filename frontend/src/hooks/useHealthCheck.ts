import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/api/client";

interface HealthResponse {
  status: "ok";
  environment: string;
}

/**
 * Polls the backend `/health` endpoint. This is the one real API
 * integration in the scaffold — useful for verifying the frontend,
 * backend, and Docker networking are wired together correctly.
 */
export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const { data } = await apiClient.get<HealthResponse>("/health");
      return data;
    },
    refetchInterval: 30_000,
  });
}
