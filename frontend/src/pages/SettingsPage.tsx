import { useState } from "react";
import { Copy, KeyRound, Server, ShieldCheck, UserPlus } from "lucide-react";
import { apiClient, errorMessage } from "@/api/client";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorNotice } from "@/components/common/UI";
import { useSession } from "@/hooks/useSession";
export function SettingsPage() {
  const { user } = useSession();
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <>
      <PageHeader
        eyebrow="YOUR WORKSPACE, YOUR CONTROL"
        title="Workspace settings"
        description="Connect execution workers and manage access to your cluster."
      />
      {error && <ErrorNotice message={error} />}
      <div className="settings-grid">
        <section className="panel form-panel">
          <div className="section-title">
            <Server size={21} />
            <h2>Connect a worker</h2>
          </div>
          <p className="muted">
            Run the agent on a machine with Python 3.10+ and Docker. A local CPU worker can run all
            bundled examples; GPU workloads require NVIDIA hardware and a configured GPU container
            runtime.
          </p>
          <div className="setup-step">
            <span>1</span>
            <div>
              <strong>For this local checkout</strong>
              <p>Open a terminal in the Nimbus folder and run:</p>
              <pre className="code-block">make agent</pre>
              <small>
                The launcher reads this installation’s local configuration without exposing its
                registration token.
              </small>
            </div>
          </div>
          <div className="setup-step">
            <span>2</span>
            <div>
              <strong>For another machine</strong>
              <p>Copy the worker agent and configure its registration token and API address:</p>
              <pre className="code-block">
                export NIMBUS_WORKER_TOKEN='your-token'{"\n"}python3 backend/scripts/worker_agent.py
                \{"\n"} --name gpu-worker-1 \{"\n"} --api-url https://your-nimbus-host/api/v1
              </pre>
            </div>
          </div>
          {user?.is_admin ? (
            <div className="token-controls">
              <button
                className="button secondary"
                onClick={() => {
                  void apiClient
                    .get<{ token: string }>("/auth/worker-token")
                    .then(({ data }) => setToken(data.token))
                    .catch((e) => setError(errorMessage(e)));
                }}
              >
                <KeyRound size={16} />
                {token ? "Refresh token" : "Reveal registration token"}
              </button>
              {token && (
                <div className="token-box">
                  <code>{token}</code>
                  <button
                    className="icon-button"
                    aria-label="Copy registration token"
                    onClick={() => {
                      void navigator.clipboard
                        .writeText(token)
                        .then(() => {
                          setCopied(true);
                        })
                        .catch(() =>
                          setError(
                            "Clipboard access is unavailable. Select and copy the token manually."
                          )
                        );
                    }}
                  >
                    <Copy size={16} />
                  </button>
                  {copied && <span>Copied</span>}
                </div>
              )}
              <small>
                Keep this token private. It grants permission to register execution workers. Each
                agent receives a separate, expiring worker credential.
              </small>
            </div>
          ) : (
            <div className="info-notice">
              Ask an administrator for the worker registration token.
            </div>
          )}
        </section>
        <div>
          <section className="panel form-panel">
            <div className="section-title">
              <ShieldCheck size={21} />
              <h2>Your account</h2>
            </div>
            <dl className="configuration-list">
              <div>
                <dt>Username</dt>
                <dd>{user?.username}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{user?.is_admin ? "Administrator" : "Member"}</dd>
              </div>
              <div>
                <dt>Session</dt>
                <dd>Protected HTTP-only cookie</dd>
              </div>
            </dl>
            <p className="muted">
              Members can manage their own workloads. Administrators can manage all workloads and
              workers.
            </p>
          </section>
          {user?.is_admin && (
            <section className="panel form-panel teammate-panel">
              <div className="section-title">
                <UserPlus size={21} />
                <h2>Add a teammate</h2>
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  setBusy(true);
                  setMessage("");
                  setError("");
                  void apiClient
                    .post("/auth/users", { username, password })
                    .then(() => {
                      setMessage(`Account created for ${username}.`);
                      setUsername("");
                      setPassword("");
                    })
                    .catch((e) => setError(errorMessage(e)))
                    .finally(() => setBusy(false));
                }}
              >
                <label>
                  Username
                  <input
                    required
                    minLength={3}
                    maxLength={64}
                    pattern="[a-zA-Z0-9_.-]+"
                    autoComplete="off"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                </label>
                <label>
                  Initial password
                  <input
                    type="password"
                    required
                    minLength={10}
                    maxLength={128}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </label>
                {message && (
                  <p role="status" className="success-message">
                    {message}
                  </p>
                )}
                <button className="button secondary" disabled={busy}>
                  {busy ? "Creating…" : "Create member account"}
                </button>
              </form>
            </section>
          )}
        </div>
      </div>
    </>
  );
}
