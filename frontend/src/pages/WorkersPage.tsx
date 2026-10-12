import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowUpRight, Cpu, Pause, Play, Server } from "lucide-react";
import { apiClient, errorMessage } from "@/api/client";
import type { Worker } from "@/types/api";
import { PageHeader } from "@/components/common/PageHeader";
import { Empty, ErrorNotice, Loading, StatusBadge } from "@/components/common/UI";
import { date, memory } from "@/utils/format";
import { useSession } from "@/hooks/useSession";
export function WorkersPage() {
  const workers = useQuery({
    queryKey: ["workers"],
    queryFn: async () => (await apiClient.get<Worker[]>("/workers")).data,
    refetchInterval: 5000,
  });
  const cache = useQueryClient();
  const { user } = useSession();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  async function drain(worker: Worker) {
    setBusy(worker.id);
    setError("");
    try {
      await apiClient.post(`/workers/${worker.id}/drain`, { draining: !worker.draining });
      await cache.invalidateQueries({ queryKey: ["workers"] });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy("");
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="THE MACHINES BEHIND YOUR WORK"
        title="Connected workers"
        description="Monitor capacity, heartbeat health, and active assignments."
        action={
          <Link className="button primary" to="/settings">
            <Server size={17} />
            Connect worker
          </Link>
        }
      />
      {error && <ErrorNotice message={error} />}
      {workers.isError ? (
        <ErrorNotice
          message={errorMessage(workers.error)}
          retry={() => {
            void workers.refetch();
          }}
        />
      ) : workers.isPending ? (
        <Loading />
      ) : !workers.data?.length ? (
        <section className="panel">
          <Empty
            title="Bring your compute online"
            description="Start a Nimbus agent on a machine with Docker to execute CPU or GPU workloads."
          >
            <Link className="button primary" to="/settings">
              Connect your first worker
            </Link>
          </Empty>
        </section>
      ) : (
        <div className="worker-grid">
          {workers.data.map((worker) => (
            <section className="panel worker-card" key={worker.id}>
              <div className="worker-card-header">
                <span
                  className={`worker-server-icon ${worker.status === "OFFLINE" ? "offline" : ""}`}
                >
                  <Server size={24} />
                </span>
                <StatusBadge status={worker.status} />
              </div>
              <h2>{worker.name}</h2>
              <p>
                {worker.executor === "docker"
                  ? worker.gpu_memory
                    ? "GPU execution worker"
                    : "CPU execution worker"
                  : "Legacy worker · agent upgrade required"}
              </p>
              <div className="worker-resource-grid">
                <div>
                  <Cpu size={15} />
                  <strong>{Number(worker.cpu_capacity)}</strong>
                  <span>CPU cores</span>
                </div>
                <div>
                  <strong>{memory(worker.memory_capacity_mb)}</strong>
                  <span>RAM capacity</span>
                </div>
                <div>
                  <strong>{worker.gpu_memory ? memory(worker.gpu_memory) : "—"}</strong>
                  <span>GPU memory</span>
                </div>
              </div>
              {worker.gpu_memory > 0 && (
                <div className="worker-utilization">
                  <div>
                    <span>Reported GPU utilization</span>
                    <strong>{worker.gpu_utilization}%</strong>
                  </div>
                  <div className="progress-track">
                    <span style={{ width: `${worker.gpu_utilization}%` }} />
                  </div>
                </div>
              )}
              <div className="worker-heartbeat">
                <span className={`status-dot ${worker.status !== "OFFLINE" ? "live-dot" : ""}`} />
                Last heartbeat: {date(worker.last_heartbeat)}
              </div>
              {worker.current_job ? (
                <Link className="worker-assignment" to={`/jobs/${worker.current_job}`}>
                  View active workload
                  <ArrowUpRight size={16} />
                </Link>
              ) : (
                <div className="worker-assignment muted">
                  {worker.draining
                    ? "Paused for new assignments"
                    : worker.status === "OFFLINE"
                      ? "Waiting for agent heartbeat"
                      : "Ready for an assignment"}
                </div>
              )}
              {user?.is_admin && worker.executor === "docker" && (
                <button
                  className="button secondary full small"
                  disabled={busy === worker.id}
                  onClick={() => {
                    void drain(worker);
                  }}
                >
                  {worker.draining ? <Play size={14} /> : <Pause size={14} />}
                  {worker.draining ? "Resume assignments" : "Pause new assignments"}
                </button>
              )}
            </section>
          ))}
        </div>
      )}
    </>
  );
}
