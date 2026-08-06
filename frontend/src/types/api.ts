/**
 * Shared domain types.
 *
 * These mirror the Pydantic schemas the backend will expose. Kept minimal
 * and stable — this file grows as `app.schemas` gains real models on the
 * backend (Workload, GPUWorker, QueueEntry, ExecutionRecord, ...).
 */

export type ApiStatus = "idle" | "loading" | "success" | "error";

export interface ApiError {
  detail: string;
  status_code: number;
}
