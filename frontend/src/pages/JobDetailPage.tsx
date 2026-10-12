import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Box,
  Download,
  RotateCcw,
  Square,
  File,
  CheckCircle2,
  Clock,
  Server,
} from "lucide-react";
import { apiClient, downloadFile, errorMessage } from "@/api/client";
import type { Artifact, Job, Worker } from "@/types/api";
import { PageHeader } from "@/components/common/PageHeader";
import { Empty, ErrorNotice, Loading, StatusBadge } from "@/components/common/UI";
import { date, duration, memory } from "@/utils/format";
import { LogViewer } from "@/components/common/LogViewer";
export function JobDetailPage() {
  const { jobId = "" } = useParams();
  const navigate = useNavigate();
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["job", jobId],
    queryFn: async () => (await apiClient.get<Job>(`/jobs/${jobId}`)).data,
    refetchInterval: 2000,
  });
  const workers = useQuery({
    queryKey: ["workers"],
    queryFn: async () => (await apiClient.get<Worker[]>("/workers")).data,
  });
  const artifacts = useQuery({
    queryKey: ["artifacts", jobId],
    queryFn: async () => (await apiClient.get<Artifact[]>(`/jobs/${jobId}/artifacts`)).data,
    refetchInterval: 5000,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function act(action: "cancel" | "retry") {
    setBusy(true);
    setError("");
    try {
      const { data } = await apiClient.post<Job>(`/jobs/${jobId}/${action}`);
      await cache.invalidateQueries();
      if (action === "retry") navigate(`/jobs/${data.id}`);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  if (query.isPending) return <Loading label="Loading workload…" />;
  if (query.isError || !query.data)
    return (
      <ErrorNotice
        message={errorMessage(query.error)}
        retry={() => {
          void query.refetch();
        }}
      />
    );
  const job = query.data;
  const terminal = ["COMPLETED", "FAILED", "CANCELLED"].includes(job.status);
  const worker = workers.data?.find((w) => w.id === job.worker_id);
  const timeline = [
    { label: "Submitted", time: job.created_at, icon: Box },
    { label: "Assigned", time: job.assigned_at, icon: Server },
    { label: "Started", time: job.started_at, icon: Clock },
    {
      label: terminal
        ? job.status === "COMPLETED"
          ? "Completed"
          : job.status === "CANCELLED"
            ? "Cancelled"
            : "Failed"
        : "Finished",
      time: job.completed_at,
      icon: CheckCircle2,
    },
  ];
  return (
    <>
      <Link className="back-link" to="/queue">
        <ArrowLeft size={15} />
        Back to workloads
      </Link>
      <PageHeader
        eyebrow={`WORKLOAD / ${job.id.slice(0, 8)}`}
        title={job.title}
        description={`Submitted ${date(job.created_at)} · ${job.command.length ? "Container execution" : "Legacy record from before real execution was available"}`}
        action={
          <div className="inline-actions">
            <StatusBadge status={job.status} cancelling={job.cancel_requested && !terminal} />
            {terminal ? (
              <button
                className="button secondary"
                disabled={busy || !job.command.length}
                onClick={() => {
                  void act("retry");
                }}
              >
                <RotateCcw size={16} />
                Retry workload
              </button>
            ) : (
              <button
                className="button danger"
                disabled={busy || job.cancel_requested}
                onClick={() => {
                  void act("cancel");
                }}
              >
                <Square size={14} />
                {job.cancel_requested ? "Cancellation requested" : "Cancel workload"}
              </button>
            )}
          </div>
        }
      />
      {error && <ErrorNotice message={error} />}
      {job.waiting_reason && (
        <div className="info-notice">
          <Clock size={18} />
          {job.waiting_reason}
        </div>
      )}
      {job.failure_reason && <ErrorNotice message={job.failure_reason} />}
      <div className="detail-metrics">
        <div>
          <span>Worker</span>
          <strong>{worker?.name ?? "Unassigned"}</strong>
        </div>
        <div>
          <span>Requested resources</span>
          <strong>
            {Number(job.cpu_request)} CPU · {memory(job.memory_limit_mb)} RAM
            {job.gpu_memory_request ? ` · ${memory(job.gpu_memory_request)} GPU` : ""}
          </strong>
        </div>
        <div>
          <span>Duration</span>
          <strong>{duration(job.started_at, job.completed_at)}</strong>
        </div>
        <div>
          <span>Exit code</span>
          <strong>{job.exit_code ?? "—"}</strong>
        </div>
      </div>
      <section className="panel timeline-panel">
        {timeline.map((stage) => (
          <div className={`timeline-stage ${stage.time ? "complete" : ""}`} key={stage.label}>
            <span>
              <stage.icon size={18} />
            </span>
            <div>
              <strong>{stage.label}</strong>
              <small>{date(stage.time)}</small>
            </div>
          </div>
        ))}
      </section>
      <LogViewer jobId={jobId} />
      <div className="detail-bottom-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Execution configuration</h2>
            <Box size={18} />
          </div>
          <dl className="configuration-list">
            <div>
              <dt>Image</dt>
              <dd className="mono">{job.image}</dd>
            </div>
            <div>
              <dt>Priority</dt>
              <dd>{job.priority}</dd>
            </div>
            <div>
              <dt>Timeout</dt>
              <dd>{job.timeout_seconds}s</dd>
            </div>
            <div>
              <dt>GPU requirement</dt>
              <dd>{job.gpu_memory_request ? memory(job.gpu_memory_request) : "CPU only"}</dd>
            </div>
            {job.retry_of && (
              <div>
                <dt>Retry of</dt>
                <dd>
                  <Link className="text-link" to={`/jobs/${job.retry_of}`}>
                    {job.retry_of.slice(0, 8)}
                  </Link>
                </dd>
              </div>
            )}
          </dl>
          <details className="command-details">
            <summary>View command arguments</summary>
            <pre>{JSON.stringify(job.command, null, 2)}</pre>
          </details>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <h2>Output files</h2>
            <File size={18} />
          </div>
          {artifacts.isError ? (
            <ErrorNotice message={errorMessage(artifacts.error)} />
          ) : artifacts.data?.length ? (
            <div className="artifact-list">
              {artifacts.data.map((file) => (
                <div className="artifact" key={file.id}>
                  <File size={19} />
                  <div>
                    <strong>{file.filename}</strong>
                    <small>
                      {file.size < 1024 ? `${file.size} B` : `${(file.size / 1024).toFixed(1)} KB`}
                    </small>
                  </div>
                  <button
                    className="icon-button"
                    aria-label={`Download ${file.filename}`}
                    onClick={() => {
                      void downloadFile(`/jobs/${jobId}/artifacts/${file.id}`, file.filename).catch(
                        (e) => setError(errorMessage(e))
                      );
                    }}
                  >
                    <Download size={18} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title={terminal ? "No output files" : "Results will land here"}
              description={
                terminal
                  ? "This workload did not produce downloadable files."
                  : "Files written to /output are collected when the workload finishes."
              }
            />
          )}
        </section>
      </div>
    </>
  );
}
