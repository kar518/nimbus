import { LayoutDashboard } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";

export function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="Cluster-wide overview of queue depth, worker utilization, and recent activity."
      />
      <EmptyState
        icon={LayoutDashboard}
        title="No data source connected yet"
        description="This page will summarize queue status, GPU utilization, and recent job activity once the API endpoints and data hooks are implemented."
      />
    </>
  );
}
