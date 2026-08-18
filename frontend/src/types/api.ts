export type ApiStatus="idle"|"loading"|"success"|"error";
export type WorkerStatus="IDLE"|"BUSY"|"OFFLINE"; export type JobStatus="QUEUED"|"RUNNING"|"COMPLETED"|"FAILED";
export interface Worker{id:string;name:string;status:WorkerStatus;gpu_memory:number;gpu_utilization:number;current_job:string|null;last_heartbeat:string|null;created_at:string}
export interface Job{id:string;title:string;status:JobStatus;priority:number;owner_id:string|null;worker_id:string|null;cpu_request:string;gpu_memory_request:number;estimated_runtime:number;created_at:string;started_at:string|null;completed_at:string|null}
export interface ApiError{detail:string;status_code:number}
