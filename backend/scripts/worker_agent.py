"""
Minimal Nimbus worker agent.

This simulates what a real GPU worker's own agent process would do:
register itself with the Nimbus API, then heartbeat on a fixed interval
for as long as it's alive. It does *not* execute jobs itself — job
lifecycle (RUNNING -> COMPLETED/FAILED) is still owned by
`app.workers.tasks.execution` on the backend, per the scaffold's current
scope (see `README.md` roadmap). This script exists purely to give the
scheduler real, heartbeating workers to assign queued jobs to, so the
dashboard/WebSocket pipeline can be exercised end to end.

Usage:
    python scripts/worker_agent.py --name gpu-node-1 --gpu-memory 24576
    python scripts/worker_agent.py --name gpu-node-2 --gpu-memory 16384 \\
        --api-url http://localhost:8000/api/v1 --interval 15

Run one process per simulated worker. Ctrl+C to stop (the worker will
simply stop heartbeating and the backend's stale-worker check will flip
it to OFFLINE after WORKER_HEARTBEAT_TIMEOUT_SECONDS).
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx


def get_or_create_worker(client: httpx.Client, name: str, gpu_memory: int) -> str:
    """Return the worker's id, creating it if a worker with this name
    doesn't already exist (so re-running the script after a restart
    doesn't fail on the unique name constraint)."""
    resp = client.get("/workers")
    resp.raise_for_status()
    for worker in resp.json():
        if worker["name"] == name:
            print(f"[worker_agent] found existing worker '{name}' (id={worker['id']})")
            return worker["id"]

    resp = client.post("/workers", json={"name": name, "gpu_memory": gpu_memory})
    resp.raise_for_status()
    worker = resp.json()
    print(f"[worker_agent] registered new worker '{name}' (id={worker['id']})")
    return worker["id"]


def run(api_url: str, name: str, gpu_memory: int, interval: float) -> None:
    with httpx.Client(base_url=api_url, timeout=10.0) as client:
        worker_id = get_or_create_worker(client, name, gpu_memory)

        print(f"[worker_agent] heartbeating every {interval}s (Ctrl+C to stop)")
        while True:
            try:
                resp = client.post(f"/workers/{worker_id}/heartbeat")
                resp.raise_for_status()
                status = resp.json()["status"]
                print(f"[worker_agent] heartbeat ok, status={status}")
            except httpx.HTTPError as exc:
                print(f"[worker_agent] heartbeat failed: {exc}", file=sys.stderr)

            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulated Nimbus GPU worker agent.")
    parser.add_argument("--name", required=True, help="Unique worker name, e.g. gpu-node-1")
    parser.add_argument("--gpu-memory", type=int, required=True, help="GPU memory in MB")
    parser.add_argument(
        "--api-url", default="http://localhost:8000/api/v1", help="Nimbus API base URL"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=15.0,
        help="Heartbeat interval in seconds (match WORKER_HEARTBEAT_INTERVAL_SECONDS)",
    )
    args = parser.parse_args()

    try:
        run(args.api_url, args.name, args.gpu_memory, args.interval)
    except KeyboardInterrupt:
        print("\n[worker_agent] stopped")


if __name__ == "__main__":
    main()
