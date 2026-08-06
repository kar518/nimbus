import { Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { DashboardPage } from "@/pages/DashboardPage";
import { ExecutionHistoryPage } from "@/pages/ExecutionHistoryPage";
import { LogsPage } from "@/pages/LogsPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { QueuePage } from "@/pages/QueuePage";
import { WorkersPage } from "@/pages/WorkersPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/queue" element={<QueuePage />} />
        <Route path="/workers" element={<WorkersPage />} />
        <Route path="/history" element={<ExecutionHistoryPage />} />
        <Route path="/logs" element={<LogsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  );
}
