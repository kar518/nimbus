import { History } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";

export function ExecutionHistoryPage() {
  return (
    <>
      <PageHeader
        title="Execution History"
        description="Completed, failed, and cancelled workloads with timing and outcome."
      />
      <EmptyState
        icon={History}
        title="No execution history yet"
        description="This page will show a searchable, filterable history of finished workloads once execution tracking is implemented."
      />
    </>
  );
}
