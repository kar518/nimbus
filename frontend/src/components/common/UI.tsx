import { AlertCircle, Cloud, Loader2 } from "lucide-react";
import type { PropsWithChildren } from "react";
import type { JobStatus, WorkerStatus } from "@/types/api";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="brand">
      <span className="brand-icon">
        <Cloud size={22} strokeWidth={2.2} />
      </span>
      {!compact && (
        <span>
          Nimbus<span className="brand-period">.</span>
        </span>
      )}
    </div>
  );
}
export function StatusBadge({
  status,
  cancelling = false,
}: {
  status: JobStatus | WorkerStatus;
  cancelling?: boolean;
}) {
  return (
    <span className={`status-badge status-${status.toLowerCase()}`}>
      <span className="status-dot" />
      {cancelling ? "Cancelling" : status === "ASSIGNED" ? "Starting" : status.toLowerCase()}
    </span>
  );
}
export function Loading({ label = "Loading workspace…" }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <Loader2 className="spin" size={20} />
      {label}
    </div>
  );
}
export function ErrorNotice({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="error-notice" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
      {retry && (
        <button className="button small ghost" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function Empty({
  title,
  description,
  children,
}: PropsWithChildren<{ title: string; description: string }>) {
  return (
    <div className="empty-state">
      <Cloud size={32} />
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}
