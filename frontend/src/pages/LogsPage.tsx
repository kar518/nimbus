import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient, errorMessage } from "@/api/client";
import type { Job } from "@/types/api";
import { PageHeader } from "@/components/common/PageHeader";
import { LogViewer } from "@/components/common/LogViewer";
import { Empty, ErrorNotice, Loading } from "@/components/common/UI";
export function LogsPage() {
  const [selected, setSelected] = useState("");
  const jobs = useQuery({
    queryKey: ["jobs", "log-selector"],
    queryFn: async () => (await apiClient.get<Job[]>("/jobs", { params: { limit: 100 } })).data,
    refetchInterval: 10000,
  });
  const id =
    selected || jobs.data?.find((job) => job.status === "RUNNING")?.id || jobs.data?.[0]?.id;
  return (
    <>
      <PageHeader
        eyebrow="THE DETAILS BEHIND THE OUTCOME"
        title="Execution logs"
        description="Follow live output or inspect retained logs from a recent workload."
      />
      {jobs.isPending ? (
        <Loading />
      ) : jobs.isError ? (
        <ErrorNotice message={errorMessage(jobs.error)} />
      ) : !jobs.data?.length ? (
        <section className="panel">
          <Empty
            title="No executions to inspect"
            description="Submit a workload to start capturing its output."
          />
        </section>
      ) : (
        <>
          <div className="log-selector">
            <label>
              Workload
              <select value={id} onChange={(e) => setSelected(e.target.value)}>
                {jobs.data.map((job) => (
                  <option value={job.id} key={job.id}>
                    {job.title} · {job.status.toLowerCase()}
                  </option>
                ))}
              </select>
            </label>
            <p>
              Showing your 100 most recent workloads. Older logs are available from each workload’s
              detail page.
            </p>
          </div>
          {id && <LogViewer key={id} jobId={id} />}
        </>
      )}
    </>
  );
}
