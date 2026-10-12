import { Link, useLocation } from "react-router-dom";
import { Cloud, Plus } from "lucide-react";
import { useHealthCheck } from "@/hooks/useHealthCheck";
import { NAV_ITEMS } from "@/utils/navigation";
export function Topbar({ live }: { live: boolean }) {
  const location = useLocation();
  const current = NAV_ITEMS.find((item) =>
    item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to)
  );
  const health = useHealthCheck();
  return (
    <header className="topbar">
      <div className="breadcrumbs">
        <Cloud size={16} />
        <span>Workspace</span>
        <span className="breadcrumb-slash">/</span>
        <strong>{current?.label ?? "Workload"}</strong>
      </div>
      <div className="topbar-actions">
        <span className="connection-status">
          <span className={`status-dot ${health.data ? "live-dot" : "warning-dot"}`} />
          {health.isError
            ? "API unavailable"
            : !health.data
              ? "Connecting…"
              : live
                ? "Live updates"
                : "Polling updates"}
        </span>
        <Link className="button small primary" to="/jobs/new">
          <Plus size={15} />
          New workload
        </Link>
      </div>
    </header>
  );
}
