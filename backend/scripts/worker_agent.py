#!/usr/bin/env python3
"""Nimbus Docker worker. Uses only Python's standard library; no Docker socket mount."""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import queue
import re
import signal
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger("nimbus.agent")
STOP = threading.Event()


class APIError(RuntimeError):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status


class Client:
    def __init__(self, base_url: str, token: str):
        self.base = base_url.rstrip("/")
        self.token = token

    def request(self, method: str, path: str, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        request = urllib.request.Request(
            self.base + path,
            data=payload,
            method=method,
            headers={"Authorization": "Bearer " + self.token, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                detail = json.load(exc).get("detail", "API request failed")
            except (ValueError, OSError):
                detail = "API request failed"
            raise APIError(exc.code, str(detail)) from exc

    def reliable(self, method: str, path: str, data=None):
        last_error = None
        for attempt in range(6):
            try:
                return self.request(method, path, data)
            except APIError as exc:
                if exc.status < 500 and exc.status != 429:
                    raise
                last_error = exc
            except (OSError, ValueError) as exc:
                last_error = exc
            time.sleep(min(2**attempt, 10))
        raise RuntimeError("The API remained unavailable after retries.") from last_error


def docker_info():
    result = subprocess.run(
        ["docker", "info", "--format", "{{json .}}"],
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    info = json.loads(result.stdout)
    return info["NCPU"], max(64, int(info["MemTotal"] / (1024 * 1024)) - 256)


def gpu_info():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        # One container per agent; advertise the largest GPU, not a fictitious pooled device.
        values = [
            tuple(int(part.strip()) for part in line.split(","))
            for line in result.stdout.splitlines()
        ]
        return max(values, default=(0, 0))
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0, 0


def stop_container(name: str):
    subprocess.run(
        ["docker", "kill", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=15,
        check=False,
    )


def collect_artifacts(directory: Path):
    artifacts = []
    total = 0
    for path in sorted(directory.iterdir()):
        if (
            path.is_symlink()
            or not path.is_file()
            or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", path.name)
        ):
            continue
        size = path.stat().st_size
        if size > 2 * 1024 * 1024 or total + size > 8 * 1024 * 1024 or len(artifacts) >= 8:
            log.warning("Skipping output outside artifact limits: %s", path.name)
            continue
        total += size
        artifacts.append(
            {"filename": path.name, "content_base64": base64.b64encode(path.read_bytes()).decode()}
        )
    return artifacts


def execute(client: Client, worker_id: str, assignment):
    job = assignment["job"]
    token = assignment["execution_token"]
    path = f"/workers/{worker_id}/jobs/{job['id']}"
    client.reliable("POST", path + "/claim", {"execution_token": token})
    name = "nimbus-job-" + job["id"] + "-" + token[:8]
    offset = 0
    reason = None
    exit_code = 1
    artifacts = []
    started = time.monotonic()
    pending = ""
    last_flush = 0.0
    last_control = 0.0
    output = queue.Queue(maxsize=128)
    with tempfile.TemporaryDirectory(prefix="nimbus-output-") as directory:
        output_dir = Path(directory)
        output_dir.chmod(0o700)
        arguments = [
            "docker",
            "run",
            "--name",
            name,
            "--label",
            "nimbus.managed=true",
            "--label",
            "nimbus.job=" + job["id"],
            "--cpus",
            str(job["cpu_request"]),
            "--memory",
            f"{job['memory_limit_mb']}m",
            "--memory-swap",
            f"{job['memory_limit_mb']}m",
            "--pids-limit",
            "128",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--mount",
            f"type=bind,src={directory},dst=/output",
            "--workdir",
            "/output",
        ]
        if job["gpu_memory_request"] > 0:
            arguments += ["--gpus", "all"]
        arguments += [job["image"], *job["command"]]
        log.info("Executing %s (%s)", job["title"], job["id"])
        process = None
        try:
            process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            def read_output():
                if process is None or process.stdout is None:
                    return
                while True:
                    data = process.stdout.readline(4096)
                    if not data:
                        break
                    output.put(data.decode("utf-8", errors="replace"))
                output.put(None)

            reader = threading.Thread(target=read_output, daemon=True)
            reader.start()
            stream_done = False
            while not stream_done:
                try:
                    chunk = output.get(timeout=0.25)
                    if chunk is None:
                        stream_done = True
                    else:
                        pending += chunk
                except queue.Empty:
                    pass
                timestamp = time.monotonic()
                if not reason and (STOP.is_set() or timestamp - started > job["timeout_seconds"]):
                    reason = (
                        "Agent stopped during execution."
                        if STOP.is_set()
                        else f"Execution exceeded its {job['timeout_seconds']} second timeout."
                    )
                    stop_container(name)
                    if process.poll() is None:
                        process.terminate()
                if timestamp - last_control >= 2 and not reason:
                    control = client.reliable("POST", path + "/control", {"execution_token": token})
                    last_control = timestamp
                    if control["cancel"]:
                        reason = "Cancelled by operator."
                        stop_container(name)
                        if process.poll() is None:
                            process.terminate()
                if pending and (
                    timestamp - last_flush > 0.5 or len(pending) >= 8192 or stream_done
                ):
                    while pending:
                        batch, pending = pending[:16384], pending[16384:]
                        result = client.reliable(
                            "POST",
                            path + "/logs",
                            {"execution_token": token, "offset": offset, "text": batch},
                        )
                        offset = result["offset"]
                    last_flush = timestamp
            exit_code = process.wait(timeout=15)
            artifacts = collect_artifacts(output_dir)
        except Exception as exc:
            reason = f"Worker execution error: {str(exc)[:1000]}"
            log.warning("Execution interrupted: %s", reason)
        finally:
            try:
                subprocess.run(
                    ["docker", "rm", "-f", name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=20,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                log.warning("Could not remove container %s", name)
            if process and process.poll() is None:
                process.kill()
                process.wait(timeout=10)
        client.reliable(
            "POST",
            path + "/finish",
            {
                "execution_token": token,
                "exit_code": exit_code,
                "reason": reason,
                "artifacts": artifacts,
            },
        )
        log.info("Reported outcome for %s: exit=%s", job["id"], exit_code)


def run(api_url: str, name: str, token: str):
    cpu, memory = docker_info()
    gpu_memory, utilization = gpu_info()
    client = Client(api_url, token)
    registration = client.reliable(
        "POST",
        "/workers/register",
        {
            "name": name,
            "cpu_capacity": cpu,
            "memory_capacity_mb": memory,
            "gpu_memory": gpu_memory,
            "gpu_utilization": utilization,
            "executor": "docker",
        },
    )
    worker_id = registration["worker"]["id"]
    client.token = registration["token"]
    log.info("Registered %s: %s CPU cores, %s MB RAM, %s MB GPU", name, cpu, memory, gpu_memory)

    def heartbeat_loop():
        while not STOP.is_set():
            try:
                _, usage = gpu_info()
                client.request(
                    "POST", f"/workers/{worker_id}/heartbeat", {"gpu_utilization": usage}
                )
            except Exception:
                log.warning("Heartbeat failed; retrying in five seconds.")
            STOP.wait(5)

    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    while not STOP.is_set():
        try:
            assignment = client.request("GET", f"/workers/{worker_id}/assignment")
            if assignment:
                execute(client, worker_id, assignment)
        except APIError as exc:
            log.warning("Worker API: %s", exc)
            if exc.status in {401, 403}:
                STOP.set()
        except Exception:
            log.exception("Worker cycle failed")
        STOP.wait(2)
    try:
        client.request("POST", f"/workers/{worker_id}/offline", {})
    except Exception:
        log.warning("Could not report shutdown; the heartbeat lease will expire.")
    log.info("Agent stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Run actual Nimbus jobs in isolated Docker containers."
    )
    parser.add_argument("--name", default="local-cpu")
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1")
    parser.add_argument(
        "--token-file", type=Path, help="File containing the worker registration token"
    )
    args = parser.parse_args()
    token = (
        args.token_file.read_text().strip()
        if args.token_file
        else os.environ.get("NIMBUS_WORKER_TOKEN", "")
    )
    if not token:
        parser.error(
            "Set NIMBUS_WORKER_TOKEN or use --token-file. "
            "An administrator can obtain it from Settings."
        )
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    run(args.api_url, args.name, token)


if __name__ == "__main__":
    main()
