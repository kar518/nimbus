export type WorkerStatus = "IDLE" | "BUSY" | "OFFLINE";
export type JobStatus = "QUEUED" | "ASSIGNED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";
export interface Worker {
  id: string;
  name: string;
  status: WorkerStatus;
  gpu_memory: number;
  gpu_utilization: number;
  cpu_capacity: string;
  memory_capacity_mb: number;
  executor: string;
  draining: boolean;
  current_job: string | null;
  last_heartbeat: string | null;
  created_at: string;
}
export interface Job {
  id: string;
  title: string;
  status: JobStatus;
  priority: number;
  owner_id: string | null;
  worker_id: string | null;
  cpu_request: string;
  gpu_memory_request: number;
  estimated_runtime: number;
  image: string;
  command: string[];
  memory_limit_mb: number;
  timeout_seconds: number;
  cancel_requested: boolean;
  exit_code: number | null;
  failure_reason: string | null;
  retry_of: string | null;
  waiting_reason: string | null;
  created_at: string;
  assigned_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}
export interface Summary {
  counts: Partial<Record<JobStatus, number>>;
  total: number;
  success_rate: number | null;
  executions: number;
  daily: { date: string; count: number }[];
}
export interface User {
  username: string;
  is_admin: boolean;
}
export interface Artifact {
  id: string;
  filename: string;
  size: number;
}
export interface LogStream {
  text: string;
  offset: number;
  status: JobStatus;
  truncated: boolean;
}
