import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NewJobPage } from "@/pages/NewJobPage";
import { JobDetailPage } from "@/pages/JobDetailPage";
import type { Job } from "@/types/api";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("@/api/client", () => ({
  apiClient: api,
  errorMessage: (error: Error) => error.message,
  downloadFile: vi.fn(),
}));

function show(element: React.ReactNode, path: string) {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={cache}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/jobs/new" element={element} />
          <Route
            path="/jobs/:jobId"
            element={path === "/jobs/new" ? <div>Workload created</div> : element}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const job: Job = {
  id: "test-job",
  title: "Active workload",
  status: "RUNNING",
  priority: 0,
  owner_id: null,
  worker_id: null,
  cpu_request: "1",
  gpu_memory_request: 0,
  estimated_runtime: 0,
  image: "python:3.12-slim",
  command: ["python", "-c", "print(1)"],
  memory_limit_mb: 512,
  timeout_seconds: 300,
  cancel_requested: false,
  exit_code: null,
  failure_reason: null,
  retry_of: null,
  waiting_reason: null,
  created_at: "2026-10-11T10:00:00",
  assigned_at: "2026-10-11T10:00:01",
  started_at: "2026-10-11T10:00:02",
  completed_at: null,
};

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
});

describe("workload workflows", () => {
  it("submits an executable template with limits and navigates to the created job", async () => {
    api.post.mockResolvedValue({ data: { ...job, status: "QUEUED" } });
    show(<NewJobPage />, "/jobs/new");
    fireEvent.change(screen.getByLabelText("Workload name"), {
      target: { value: "My first execution" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Submit workload" }));
    await screen.findByText("Workload created");
    expect(api.post).toHaveBeenCalledWith(
      "/jobs",
      expect.objectContaining({
        title: "My first execution",
        command: ["python", "-u", "-c", expect.stringContaining("/output/result.json")],
        memory_limit_mb: 512,
        timeout_seconds: 300,
        gpu_memory_request: 0,
      })
    );
  });

  it("rejects a malformed custom command before sending a job", async () => {
    show(<NewJobPage />, "/jobs/new");
    fireEvent.click(screen.getByLabelText("Use a custom command instead of a Python script"));
    fireEvent.change(screen.getByLabelText(/Command arguments/), { target: { value: "[]" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit workload" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("non-empty JSON array");
    expect(api.post).not.toHaveBeenCalled();
  });

  it("requests cancellation and keeps the job running until worker confirmation", async () => {
    let current = job;
    api.get.mockImplementation(async (path: string) => ({
      data: path.endsWith("/logs")
        ? { text: "Still running", offset: 13, status: "RUNNING", truncated: false }
        : path.endsWith("/artifacts") || path === "/workers"
          ? []
          : current,
    }));
    api.post.mockImplementation(async () => {
      current = { ...job, cancel_requested: true };
      return { data: current };
    });
    show(<JobDetailPage />, "/jobs/test-job");
    fireEvent.click(await screen.findByRole("button", { name: "Cancel workload" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Cancellation requested" })).toBeDisabled()
    );
    expect(api.post).toHaveBeenCalledWith("/jobs/test-job/cancel");
    expect(screen.getByText("Cancelling")).toBeInTheDocument();
    expect(screen.getByText("Still running")).toBeInTheDocument();
  });
});
