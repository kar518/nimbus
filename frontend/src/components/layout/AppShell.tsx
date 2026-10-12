import type { PropsWithChildren } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useLiveUpdates } from "@/hooks/useClusterData";
export function AppShell({ children }: PropsWithChildren) {
  const live = useLiveUpdates();
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <Sidebar />
      <div className="main-column">
        <Topbar live={live} />
        <main id="main-content" className="main-content">
          {children}
          <footer className="page-footer">
            <span>Nimbus · compute with clarity</span>
            <span>Isolated execution. Observable outcomes.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
