import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Box,
  CheckCircle2,
  Cpu,
  Layers,
  Plus,
  Server,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useClusterData } from "@/hooks/useClusterData";
import { errorMessage } from "@/api/client";
import { PageHeader } from "@/components/common/PageHeader";
import { JobTable } from "@/components/common/JobTable";
import { Empty, ErrorNotice, Loading, StatusBadge } from "@/components/common/UI";
import { memory } from "@/utils/format";
export function DashboardPage() {
  const { workers, jobs, summary, loading, error } = useClusterData();
  const online = workers.filter((w) => w.status !== "OFFLINE" && w.executor === "docker");
  const busy = online.filter((w) => w.status === "BUSY").length;
  const cpu = online.reduce((sum, worker) => sum + Number(worker.cpu_capacity), 0);
  const gpu = online.reduce((sum, worker) => sum + worker.gpu_memory, 0);
  const max = Math.max(1, ...(summary?.daily.map((day) => day.count) ?? []));
  const cards = [
    {
      label: "ONLINE WORKERS",
      value: online.length,
      detail: `${busy} busy · ${online.length - busy} available`,
      icon: Server,
      color: "blue",
    },
    {
      label: "RUNNING WORKLOADS",
      value: summary?.counts.RUNNING ?? 0,
      detail: `${summary?.counts.ASSIGNED ?? 0} starting on workers`,
      icon: Activity,
      color: "green",
    },
    {
      label: "IN THE QUEUE",
      value: summary?.counts.QUEUED ?? 0,
      detail: "Priority first, then submission time",
      icon: Layers,
      color: "orange",
    },
    {
      label: "SUCCESS RATE",
      value: summary?.success_rate == null ? "—" : `${summary.success_rate}%`,
      detail: `${summary?.executions ?? 0} actual executions`,
      icon: CheckCircle2,
      color: "purple",
    },
  ];
  return (
    <>
      <PageHeader
        eyebrow="YOUR COMPUTE, AT A GLANCE"
        title="Everything in sync."
        description="A clear view of your workloads, workers, and what comes next."
        action={
          <Link className="button primary" to="/jobs/new">
            <Plus size={17} />
            Submit workload
          </Link>
        }
      />
      {error && <ErrorNotice message={errorMessage(error)} />}
      {loading ? (
        <Loading />
      ) : (
        <>
          <div className="metric-grid">
            {cards.map((card) => (
              <div className="metric-card" key={card.label}>
                <div className="metric-label">
                  {card.label}
                  <span className={`metric-icon ${card.color}`}>
                    <card.icon size={18} />
                  </span>
                </div>
                <strong className="metric-value">{card.value}</strong>
                <p>{card.detail}</p>
              </div>
            ))}
          </div>
          <div className="overview-grid">
            <section className="panel activity-panel">
              <div className="panel-heading">
                <div>
                  <h2>Workload activity</h2>
                  <p>Submissions over the last seven days · UTC</p>
                </div>
                <span className="pill">7 days</span>
              </div>
              <div
                className="activity-chart"
                role="img"
                aria-label={`Daily submissions: ${summary?.daily.map((day) => `${day.date}: ${day.count}`).join(", ")}`}
              >
                <div className="chart-grid" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                </div>
                {summary?.daily.map((day) => (
                  <div className="chart-column" key={day.date}>
                    <span className="bar-count">{day.count || ""}</span>
                    <div
                      className={`chart-bar ${day.count ? "has-value" : ""}`}
                      style={{
                        height: `${Math.max(day.count ? 7 : 1, (day.count / max) * 130)}px`,
                      }}
                    />
                    <span className="chart-day">
                      {new Date(day.date + "T12:00:00Z").toLocaleDateString(undefined, {
                        weekday: "short",
                        timeZone: "UTC",
                      })}
                    </span>
                  </div>
                ))}
              </div>
              <div className="activity-total">
                <span>
                  <Box size={16} />
                  {summary?.daily.reduce((sum, day) => sum + day.count, 0)} submissions this week
                </span>
                <Link to="/history">
                  Explore history
                  <ArrowUpRight size={15} />
                </Link>
              </div>
            </section>
            <section className="panel capacity-panel">
              <div className="panel-heading">
                <div>
                  <h2>Cluster capacity</h2>
                  <p>Reported by online execution agents</p>
                </div>
                <Cpu size={19} />
              </div>
              <div className="capacity-big">
                <strong>
                  {cpu}
                  <span>cores</span>
                </strong>
                <span className="capacity-label">Available cluster CPU capacity</span>
              </div>
              <div className="capacity-line">
                <span>GPU memory</span>
                <strong>{gpu ? memory(gpu) : "No GPU connected"}</strong>
              </div>
              <div className="capacity-line">
                <span>Worker occupancy</span>
                <strong>
                  {busy} / {online.length}
                </strong>
              </div>
              <div className="progress-track">
                <span style={{ width: `${online.length ? (busy / online.length) * 100 : 0}%` }} />
              </div>
              <p className="capacity-note">Each worker runs one isolated container at a time.</p>
              <Link className="text-link" to="/workers">
                Manage workers
                <ArrowRight size={15} />
              </Link>
            </section>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Recent workloads</h2>
                <p>The latest work moving through your cluster</p>
              </div>
              <Link className="text-link" to="/queue">
                View all
                <ArrowRight size={15} />
              </Link>
            </div>
            {jobs.length ? (
              <JobTable jobs={jobs} workers={workers} />
            ) : (
              <Empty
                title="Your next workload starts here"
                description="Submit an example or bring your own container command."
              >
                <Link className="button primary" to="/jobs/new">
                  <Plus size={16} />
                  Create workload
                </Link>
              </Empty>
            )}
          </section>
          <section className="worker-strip">
            <div>
              <h2>Connected compute</h2>
              <p>
                {online.length
                  ? "Workers ready to turn commands into results."
                  : "Connect a worker to start executing your workloads."}
              </p>
            </div>
            <div className="worker-strip-items">
              {online.slice(0, 3).map((worker) => (
                <Link className="worker-chip" to="/workers" key={worker.id}>
                  <Server size={16} />
                  <strong>{worker.name}</strong>
                  <StatusBadge status={worker.status} />
                </Link>
              ))}
              <Link className="text-link" to="/settings">
                Connect worker
                <ArrowUpRight size={16} />
              </Link>
            </div>
          </section>
        </>
      )}
    </>
  );
}
