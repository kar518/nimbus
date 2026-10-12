import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  timeout: 15_000,
  withCredentials: true,
});

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return "Some fields are invalid. Check your workload settings.";
    return error.response
      ? "This request could not be completed. Please try again."
      : "Nimbus is unreachable. Check your connection and try again.";
  }
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

export async function downloadFile(path: string, filename: string) {
  const { data } = await apiClient.get<Blob>(path, { responseType: "blob" });
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
