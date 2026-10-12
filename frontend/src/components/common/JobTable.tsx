import { ArrowUpRight, Box } from "lucide-react";
import { Link } from "react-router-dom";
import type { Job, Worker } from "@/types/api";
import { StatusBadge } from "./UI";
import { date, duration, memory } from "@/utils/format";
export function JobTable({ jobs, workers = [] }: { jobs: Job[]; workers?: Worker[] }) {
  return (
    <div className="table-scroll">
      <table className="job-table">
        <thead>
          <tr>
            <th>Workload</th>
            <th>Status</th>
            <th>Resources</th>
            <th>Worker</th>
            <th>Duration</th>
            <th>Submitted</th>
            <th>
              <span className="sr-only">Details</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>
                <Link className="workload-link" to={`/jobs/${job.id}`}>
                  <span className="workload-icon">
                    <Box size={17} />
                  </span>
                  <span>
                    <strong>{job.title}</strong>
                    <small>{job.command.length ? job.image : "Legacy record"}</small>
                  </span>
                </Link>
              </td>
              <td>
                <StatusBadge
                  status={job.status}
                  cancelling={job.cancel_requested && job.status === "RUNNING"}
                />
              </td>
              <td>
                <span className="resource-text">{Number(job.cpu_request)} CPU</span>
                <small>
                  {job.gpu_memory_request
                    ? `${memory(job.gpu_memory_request)} GPU`
                    : `${memory(job.memory_limit_mb)} RAM`}
                </small>
              </td>
              <td className="muted">
                {workers.find((w) => w.id === job.worker_id)?.name ??
                  (job.worker_id ? job.worker_id.slice(0, 8) : "Unassigned")}
              </td>
              <td className="mono muted">{duration(job.started_at, job.completed_at)}</td>
              <td className="muted nowrap">{date(job.created_at)}</td>
              <td>
                <Link
                  className="icon-button"
                  to={`/jobs/${job.id}`}
                  aria-label={`View ${job.title}`}
                >
                  <ArrowUpRight size={17} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
