import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Box,
  Check,
  Code2,
  Cpu,
  FlaskConical,
  ShieldCheck,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { apiClient, errorMessage } from "@/api/client";
import type { Job } from "@/types/api";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorNotice } from "@/components/common/UI";
const templates = [
  {
    name: "Hello Nimbus",
    description: "A small job with logs and an output file",
    icon: Box,
    title: "Hello Nimbus",
    script:
      "import json, time\nfrom pathlib import Path\nprint('Hello from your Nimbus worker!', flush=True)\nfor step in range(5):\n    print(f'Step {step + 1}/5 complete', flush=True)\n    time.sleep(1)\nPath('/output/result.json').write_text(json.dumps({'status': 'success', 'steps': 5}, indent=2))\nprint('Result saved to result.json', flush=True)",
  },
  {
    name: "CPU benchmark",
    description: "Compute primes and save the result",
    icon: Cpu,
    title: "Prime number benchmark",
    script:
      "import json, math, time\nfrom pathlib import Path\nstart = time.monotonic()\nprint('Finding primes below 100,000…', flush=True)\nprimes = [n for n in range(2, 100000) if all(n % d for d in range(2, math.isqrt(n) + 1))]\nresult = {'prime_count': len(primes), 'elapsed_seconds': round(time.monotonic() - start, 3)}\nprint(json.dumps(result, indent=2), flush=True)\nPath('/output/benchmark.json').write_text(json.dumps(result, indent=2))",
  },
  {
    name: "Failure example",
    description: "See how Nimbus captures a failed run",
    icon: FlaskConical,
    title: "Failure handling example",
    script:
      "import sys, time\nprint('Starting failure handling example', flush=True)\ntime.sleep(2)\nprint('Intentional failure: demonstrating exit-code tracking', file=sys.stderr, flush=True)\nsys.exit(1)",
  },
];
export function NewJobPage() {
  const navigate = useNavigate();
  const cache = useQueryClient();
  const [selected, setSelected] = useState(0);
  const [title, setTitle] = useState(templates[0].title);
  const [script, setScript] = useState(templates[0].script);
  const [image, setImage] = useState("python:3.12-slim");
  const [cpu, setCpu] = useState("1");
  const [gpu, setGpu] = useState("0");
  const [ram, setRam] = useState("512");
  const [timeout, setTimeoutValue] = useState("300");
  const [priority, setPriority] = useState("0");
  const [advanced, setAdvanced] = useState(false);
  const [command, setCommand] = useState('["python", "-u", "script.py"]');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit() {
    setBusy(true);
    setError("");
    try {
      const argumentsList: unknown = advanced
        ? JSON.parse(command)
        : ["python", "-u", "-c", script];
      if (
        !Array.isArray(argumentsList) ||
        !argumentsList.length ||
        argumentsList.some((arg) => typeof arg !== "string")
      )
        throw new Error("Enter the command as a non-empty JSON array of strings.");
      const { data } = await apiClient.post<Job>("/jobs", {
        title,
        image,
        command: argumentsList,
        cpu_request: cpu,
        gpu_memory_request: Number(gpu),
        memory_limit_mb: Number(ram),
        timeout_seconds: Number(timeout),
        priority: Number(priority),
        estimated_runtime: 0,
      });
      await cache.invalidateQueries({ queryKey: ["jobs"] });
      await cache.invalidateQueries({ queryKey: ["summary"] });
      navigate(`/jobs/${data.id}`);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Link className="back-link" to="/queue">
        <ArrowLeft size={15} />
        Back to workloads
      </Link>
      <PageHeader
        eyebrow="LET’S PUT YOUR COMPUTE TO WORK"
        title="Create a workload"
        description="Start with an example or define your own containerized command."
      />
      <form
        className="submission-layout"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <div className="submission-main">
          <section className="panel form-panel">
            <div className="section-title">
              <span>01</span>
              <h2>Choose a starting point</h2>
            </div>
            <div className="template-grid">
              {templates.map((template, index) => (
                <button
                  type="button"
                  className={`template-card ${selected === index ? "selected" : ""}`}
                  key={template.name}
                  onClick={() => {
                    setSelected(index);
                    setTitle(template.title);
                    setScript(template.script);
                    setAdvanced(false);
                  }}
                >
                  <template.icon size={21} />
                  <strong>{template.name}</strong>
                  <p>{template.description}</p>
                  {selected === index && <Check className="template-check" size={15} />}
                </button>
              ))}
            </div>
          </section>
          <section className="panel form-panel">
            <div className="section-title">
              <span>02</span>
              <h2>Define the workload</h2>
            </div>
            <label>
              Workload name
              <input
                required
                maxLength={255}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Model evaluation"
              />
            </label>
            <label>
              Container image
              <input
                required
                value={image}
                onChange={(e) => setImage(e.target.value)}
                placeholder="python:3.12-slim"
              />
              <small>
                Use an image compatible with a non-root user and a read-only filesystem.
              </small>
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={advanced}
                onChange={(e) => setAdvanced(e.target.checked)}
              />
              Use a custom command instead of a Python script
            </label>
            {advanced ? (
              <label>
                Command arguments
                <textarea
                  className="code-input short"
                  required
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  spellCheck={false}
                />
                <small>
                  A JSON array, such as ["python", "-u", "script.py"]. Your script must be included
                  in the image.
                </small>
              </label>
            ) : (
              <label>
                Python script
                <textarea
                  className="code-input"
                  required
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                  spellCheck={false}
                />
                <small>
                  Write output files to /output to make them downloadable after execution.
                </small>
              </label>
            )}
          </section>
          <section className="panel form-panel">
            <div className="section-title">
              <span>03</span>
              <h2>Set resource limits</h2>
            </div>
            <div className="field-grid">
              <label>
                CPU cores
                <input
                  type="number"
                  min="0.1"
                  max="128"
                  step="0.1"
                  required
                  value={cpu}
                  onChange={(e) => setCpu(e.target.value)}
                />
              </label>
              <label>
                RAM limit (MB)
                <input
                  type="number"
                  min="64"
                  max="65536"
                  required
                  value={ram}
                  onChange={(e) => setRam(e.target.value)}
                />
              </label>
              <label>
                GPU memory required (MB)
                <input
                  type="number"
                  min="0"
                  max="1048576"
                  required
                  value={gpu}
                  onChange={(e) => setGpu(e.target.value)}
                />
                <small>
                  Set 0 for CPU workloads. GPU memory is an admission requirement, not a hard VRAM
                  limit.
                </small>
              </label>
              <label>
                Timeout (seconds)
                <input
                  type="number"
                  min="1"
                  max="86400"
                  required
                  value={timeout}
                  onChange={(e) => setTimeoutValue(e.target.value)}
                />
              </label>
              <label>
                Priority
                <input
                  type="number"
                  min="0"
                  max="100"
                  required
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                />
                <small>Higher values run first. Equal priorities follow submission time.</small>
              </label>
            </div>
          </section>
        </div>
        <aside className="submission-summary panel">
          <div className="summary-icon">
            <Code2 size={25} />
          </div>
          <h2>Ready for the queue</h2>
          <p>Nimbus will match this workload to an online worker with enough capacity.</p>
          <dl>
            <div>
              <dt>Execution</dt>
              <dd>Isolated Docker container</dd>
            </div>
            <div>
              <dt>CPU</dt>
              <dd>{cpu} cores</dd>
            </div>
            <div>
              <dt>RAM</dt>
              <dd>{ram} MB</dd>
            </div>
            <div>
              <dt>GPU memory</dt>
              <dd>{Number(gpu) ? `${gpu} MB` : "Not required"}</dd>
            </div>
            <div>
              <dt>Timeout</dt>
              <dd>{timeout} seconds</dd>
            </div>
          </dl>
          <div className="security-note">
            <ShieldCheck size={17} />
            <span>Network disabled, resource limits enforced, and host files isolated.</span>
          </div>
          {error && <ErrorNotice message={error} />}
          <button className="button primary full" disabled={busy}>
            {busy ? "Submitting…" : "Submit workload"}
            <ArrowRight size={16} />
          </button>
          <p className="summary-footnote">
            Logs and results will appear on your workload’s detail page.
          </p>
        </aside>
      </form>
    </>
  );
}
