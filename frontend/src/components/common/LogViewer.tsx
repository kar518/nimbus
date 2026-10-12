import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Terminal } from "lucide-react";
import { apiClient, downloadFile, errorMessage } from "@/api/client";
import type { LogStream } from "@/types/api";
import { ErrorNotice } from "./UI";
export function LogViewer({ jobId }: { jobId: string }) {
  const logs = useQuery({
    queryKey: ["logs", jobId],
    queryFn: async () => (await apiClient.get<LogStream>(`/jobs/${jobId}/logs`)).data,
    refetchInterval: (query) =>
      ["QUEUED", "ASSIGNED", "RUNNING"].includes(query.state.data?.status ?? "RUNNING")
        ? 2000
        : false,
  });
  const [follow, setFollow] = useState(true);
  const [downloadError, setDownloadError] = useState("");
  const output = useRef<HTMLPreElement>(null);
  useEffect(() => {
    if (follow && output.current) output.current.scrollTop = output.current.scrollHeight;
  }, [follow, logs.data?.text]);
  return (
    <section className="panel terminal-panel">
      <div className="panel-heading">
        <h2>
          <Terminal size={17} />
          Execution logs
        </h2>
        <div className="inline-actions">
          <label className="checkbox-label">
            <input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} />
            Follow
          </label>
          <button
            className="button small ghost"
            disabled={!logs.data?.text}
            onClick={() => {
              void downloadFile(`/jobs/${jobId}/logs/download`, `nimbus-${jobId}.log`).catch((e) =>
                setDownloadError(errorMessage(e))
              );
            }}
          >
            <Download size={15} />
            Download
          </button>
        </div>
      </div>
      {(logs.error || downloadError) && (
        <ErrorNotice message={downloadError || errorMessage(logs.error)} />
      )}
      <pre ref={output} className="terminal-output" aria-label="Execution output">
        {logs.isPending
          ? "Connecting to log stream…"
          : logs.data?.text ||
            "No output yet. Logs will appear here when the worker starts your command."}
      </pre>
      <div className="terminal-footer">
        <span>
          <span className={`status-dot ${logs.data?.status === "RUNNING" ? "live-dot" : ""}`} />
          {logs.data?.status === "RUNNING"
            ? "Streaming output · refreshes every 2s"
            : "Retained execution output"}
        </span>
        <span>
          {logs.data?.offset ?? 0} characters
          {logs.data?.truncated ? " · 1 MB retention limit reached" : ""}
        </span>
      </div>
    </section>
  );
}
