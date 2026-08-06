import { ListOrdered } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";

export function QueuePage() {
  return (
    <>
      <PageHeader
        title="Queue"
        description="Workloads waiting for GPU capacity, ordered by scheduling priority."
      />
      <EmptyState
        icon={ListOrdered}
        title="Queue view not implemented"
        description="This page will list pending and running workloads once workload submission and the scheduler API are implemented."
      />
    </>
  );
}
