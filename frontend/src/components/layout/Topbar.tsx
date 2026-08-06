import { clsx } from "clsx";
import { useLocation } from "react-router-dom";

import { useHealthCheck } from "@/hooks/useHealthCheck";
import { NAV_ITEMS } from "@/utils/navigation";

export function Topbar() {
  const location = useLocation();
  const current = NAV_ITEMS.find((item) =>
    item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to)
  );
  const { data, isError, isPending } = useHealthCheck();

  const statusColor = isPending
    ? "bg-status-queued"
    : isError
      ? "bg-status-failed"
      : "bg-status-succeeded";

  const statusLabel = isPending
    ? "Checking API..."
    : isError
      ? "API unreachable"
      : `API ${data?.environment ?? ""} — connected`;

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-surface-800 bg-surface-950/80 px-6 backdrop-blur">
      <h1 className="text-base font-semibold text-surface-50">{current?.label ?? "Nimbus"}</h1>

      <div className="flex items-center gap-2 text-xs text-surface-400">
        <span className={clsx("h-2 w-2 rounded-full", statusColor)} aria-hidden="true" />
        {statusLabel}
      </div>
    </header>
  );
}
