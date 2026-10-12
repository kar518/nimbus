import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async () => (await apiClient.get<{ status: string }>("/ready")).data,
    refetchInterval: 15000,
  });
}
