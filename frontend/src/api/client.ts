import axios from "axios";

/**
 * Shared Axios instance for all API calls.
 *
 * Base URL comes from `VITE_API_BASE_URL` (see `.env.example`), which
 * points at the FastAPI backend's `/api/v1` prefix. Interceptors below are
 * infrastructure only — no endpoint-specific logic belongs here.
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  timeout: 15_000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Centralized place to normalize/report API errors once logging
    // and auth-refresh flows are implemented.
    return Promise.reject(error);
  }
);

/**
 * Reads the current auth token synchronously outside of React.
 * Kept as a thin indirection so the store implementation can change
 * without touching this file.
 */
function getAuthToken(): string | null {
  return null;
}
