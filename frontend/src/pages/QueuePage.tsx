import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, Plus, Search } from "lucide-react";
import { apiClient, errorMessage } from "@/api/client";
import type { Job, JobStatus, Worker } from "@/types/api";
import { PageHeader } from "@/components/common/PageHeader";
import { JobTable } from "@/components/common/JobTable";
import { Empty, ErrorNotice, Loading } from "@/components/common/UI";
export function WorkloadList({ history = false }: { history?: boolean }) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const jobs = useQuery({
    queryKey: ["jobs", history, search, status, page],
    queryFn: async () =>
      (
        await apiClient.get<Job[]>("/jobs", {
          params: { q: search, status: status || undefined, history, limit: 20, offset: page * 20 },
        })
      ).data,
    refetchInterval: 5000,
  });
  const workers = useQuery({
    queryKey: ["workers"],
    queryFn: async () => (await apiClient.get<Worker[]>("/workers")).data,
  });
  const states: JobStatus[] = history
    ? ["COMPLETED", "FAILED", "CANCELLED"]
    : ["QUEUED", "ASSIGNED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"];
  return (
    <>
      <PageHeader
        eyebrow={history ? "EVERY OUTCOME, ACCOUNTED FOR" : "FROM IDEA TO EXECUTION"}
        title={history ? "Execution history" : "Your workloads"}
        description={
          history
            ? "Inspect results, understand failures, and revisit finished work."
            : "Submit, prioritize, and follow every workload through your cluster."
        }
        action={
          <Link className="button primary" to="/jobs/new">
            <Plus size={17} />
            New workload
          </Link>
        }
      />
      <section className="panel">
        <div className="table-toolbar">
          <label className="search-field">
            <Search size={17} />
            <input
              aria-label="Search workloads"
              placeholder="Search workloads…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
            />
          </label>
          <select
            aria-label="Filter by status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(0);
            }}
          >
            <option value="">All statuses</option>
            {states.map((s) => (
              <option key={s} value={s}>
                {s === "ASSIGNED" ? "Starting" : s[0] + s.slice(1).toLowerCase()}
              </option>
            ))}
          </select>
        </div>
        {jobs.isError ? (
          <ErrorNotice
            message={errorMessage(jobs.error)}
            retry={() => {
              void jobs.refetch();
            }}
          />
        ) : jobs.isPending ? (
          <Loading label="Loading workloads…" />
        ) : jobs.data?.length ? (
          <JobTable jobs={jobs.data} workers={workers.data} />
        ) : (
          <Empty
            title={
              search || status
                ? "No matching workloads"
                : history
                  ? "A clean slate"
                  : "Ready when you are"
            }
            description={
              search || status
                ? "Try a different search or status filter."
                : history
                  ? "Finished workloads will appear here with their outcomes."
                  : "Create your first workload and let Nimbus find its worker."
            }
          >
            {!history && !search && !status && (
              <Link className="button primary" to="/jobs/new">
                Submit workload
              </Link>
            )}
          </Empty>
        )}
        <div className="table-pagination">
          <span>Page {page + 1} · up to 20 workloads per page</span>
          <div className="inline-actions">
            <button
              className="button small ghost"
              disabled={!page}
              onClick={() => setPage(page - 1)}
            >
              <ChevronLeft size={15} />
              Previous
            </button>
            <button
              className="button small ghost"
              disabled={(jobs.data?.length ?? 0) < 20}
              onClick={() => setPage(page + 1)}
            >
              Next
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
export function QueuePage() {
  return <WorkloadList />;
}
