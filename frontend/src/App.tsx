import { Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { SessionProvider, useSession } from "@/hooks/useSession";
import { AuthPage } from "@/pages/AuthPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { ExecutionHistoryPage } from "@/pages/ExecutionHistoryPage";
import { JobDetailPage } from "@/pages/JobDetailPage";
import { NewJobPage } from "@/pages/NewJobPage";
import { LogsPage } from "@/pages/LogsPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { WorkersPage } from "@/pages/WorkersPage";
import { QueuePage } from "@/pages/QueuePage";
import { SettingsPage } from "@/pages/SettingsPage";
function Workspace() {
  const { user } = useSession();
  if (!user) return <AuthPage />;
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/queue" element={<QueuePage />} />
        <Route path="/workers" element={<WorkersPage />} />
        <Route path="/history" element={<ExecutionHistoryPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/jobs/new" element={<NewJobPage />} />
        <Route path="/jobs/:jobId" element={<JobDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  );
}
export default function App() {
  return (
    <SessionProvider>
      <Workspace />
    </SessionProvider>
  );
}
