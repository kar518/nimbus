#!/usr/bin/env python3
"""Manage Nimbus's local stack and Docker execution agent."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".nimbus"
PID = STATE / "worker.pid"


def alive():
    if not PID.exists():
        return False
    try:
        result = subprocess.run(
            ["ps", "-p", PID.read_text().strip(), "-o", "command="],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(ROOT / "scripts/start_worker.py") in result.stdout
    except OSError:
        return False


def start_worker():
    if alive():
        print("Nimbus execution worker is already running.")
        return
    STATE.mkdir(exist_ok=True, mode=0o700)
    for _ in range(60):
        try:
            with urllib.request.urlopen(
                "http://localhost:8000/api/v1/ready", timeout=3
            ) as response:
                if json.load(response)["status"] == "ready":
                    break
        except (OSError, ValueError):
            pass
        time.sleep(1)
    else:
        sys.exit("Nimbus did not become ready. Check docker compose logs backend.")
    with (STATE / "worker.log").open("ab") as output:
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "scripts/start_worker.py")],
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    PID.write_text(str(process.pid))
    time.sleep(2)
    if process.poll() is not None:
        sys.exit("Worker could not start. Check .nimbus/worker.log.")
    print("Nimbus worker started. Logs: .nimbus/worker.log")


def stop_worker():
    if alive():
        os.kill(int(PID.read_text()), signal.SIGTERM)
        for _ in range(25):
            if not alive():
                break
            time.sleep(1)
        if alive():
            sys.exit("Worker is still stopping its current container. Try make stop-agent again.")
        print("Nimbus worker stopped.")
    PID.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start or stop Nimbus locally.")
    parser.add_argument("action", choices=["up", "agent", "stop-agent", "down"])
    action = parser.parse_args().action
    if action == "up":
        subprocess.run(["docker", "compose", "up", "-d", "--build"], cwd=ROOT, check=True)
        start_worker()
        print("Open http://localhost:5173 to use Nimbus.")
    elif action == "agent":
        start_worker()
    elif action == "stop-agent":
        stop_worker()
    else:
        stop_worker()
        subprocess.run(["docker", "compose", "down"], cwd=ROOT, check=True)
