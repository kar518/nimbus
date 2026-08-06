import { ScrollText } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";

export function LogsPage() {
  return (
    <>
      <PageHeader
        title="Logs"
        description="Streamed stdout/stderr for a selected workload execution."
      />
      <EmptyState
        icon={ScrollText}
        title="No log stream connected"
        description="This page will stream logs for a selected job once log capture and the streaming endpoint are implemented."
      />
    </>
  );
}
