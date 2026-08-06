import { Cpu } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";

export function WorkersPage() {
  return (
    <>
      <PageHeader
        title="GPU Workers"
        description="Registered worker nodes, their capacity, and current utilization."
      />
      <EmptyState
        icon={Cpu}
        title="No workers registered yet"
        description="This page will show live worker health and GPU utilization once worker registration and heartbeats are implemented."
      />
    </>
  );
}
