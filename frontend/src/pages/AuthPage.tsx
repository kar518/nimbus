import { useState } from "react";
import { ArrowRight, Check, Cpu, ShieldCheck, Terminal } from "lucide-react";
import { errorMessage } from "@/api/client";
import { useSession } from "@/hooks/useSession";
import { ErrorNotice, Loading, Logo } from "@/components/common/UI";
export function AuthPage() {
  const session = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [setupToken, setSetupToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (session.loading)
    return (
      <div className="auth-loading">
        <Logo />
        <Loading />
      </div>
    );
  return (
    <div className="auth-page">
      <section className="auth-story">
        <Logo />
        <div className="auth-story-body">
          <p className="eyebrow">COMPUTE WITH CLARITY</p>
          <h1>
            A home for <br />
            your next <br />
            <span>big workload.</span>
          </h1>
          <p>
            From the first command to the final result. Schedule, execute, and observe your compute
            in one place.
          </p>
          <div className="auth-flow">
            <span>
              <Cpu size={22} />
              Compute
            </span>
            <ArrowRight size={18} />
            <span>
              <Terminal size={22} />
              Execute
            </span>
            <ArrowRight size={18} />
            <span>
              <Check size={22} />
              Deliver
            </span>
          </div>
        </div>
        <div className="auth-story-footer">
          <span className="status-dot live-dot" />
          Nimbus · workload orchestration
        </div>
      </section>
      <section className="auth-form-side">
        <div className="auth-card">
          <div className="auth-shield">
            <ShieldCheck size={26} />
          </div>
          <p className="eyebrow">
            {session.setupRequired ? "YOUR WORKSPACE STARTS HERE" : "WELCOME BACK"}
          </p>
          <h2>{session.setupRequired ? "Create your workspace" : "Sign in to Nimbus"}</h2>
          <p>
            {session.setupRequired
              ? "Set up the administrator account for this installation. Your password stays private."
              : "Pick up where your workloads left off."}
          </p>
          {session.unavailable ? (
            <ErrorNotice
              message="Nimbus’s API is unavailable. Check that the services are running."
              retry={session.refresh}
            />
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setBusy(true);
                setError("");
                void session
                  .authenticate(username, password, setupToken)
                  .catch((e) => setError(errorMessage(e)))
                  .finally(() => setBusy(false));
              }}
            >
              <label>
                Username
                <input
                  autoComplete="username"
                  required
                  minLength={3}
                  maxLength={64}
                  pattern="[a-zA-Z0-9_.-]+"
                  placeholder="Your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  autoComplete={session.setupRequired ? "new-password" : "current-password"}
                  required
                  minLength={10}
                  maxLength={128}
                  placeholder={session.setupRequired ? "At least 10 characters" : "Your password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              {session.setupRequired && session.requiresSetupToken && (
                <label>
                  Deployment setup token
                  <input
                    type="password"
                    required
                    value={setupToken}
                    onChange={(e) => setSetupToken(e.target.value)}
                  />
                </label>
              )}
              {error && <ErrorNotice message={error} />}
              <button className="button primary full" disabled={busy}>
                {busy ? "Please wait…" : session.setupRequired ? "Create workspace" : "Sign in"}
                <ArrowRight size={17} />
              </button>
            </form>
          )}
          <p className="auth-note">
            <ShieldCheck size={14} />
            Protected sessions. Isolated workloads.
          </p>
        </div>
      </section>
    </div>
  );
}
