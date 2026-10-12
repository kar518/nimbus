#!/usr/bin/env python3
"""Start a local worker using this checkout's configuration, without displaying secrets."""

import hashlib
import hmac
import os
import runpy
import shlex
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
values = {}
config = root / ".env"
if config.exists():
    for line in config.read_text().splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() in {"SECRET_KEY", "WORKER_API_TOKEN"}:
            parsed = shlex.split(value, comments=True)
            values[key.strip()] = parsed[0] if parsed else ""
secret = os.environ.get("SECRET_KEY") or values.get("SECRET_KEY")
token = (
    os.environ.get("NIMBUS_WORKER_TOKEN")
    or os.environ.get("WORKER_API_TOKEN")
    or values.get("WORKER_API_TOKEN")
)
if not token and secret:
    token = hmac.new(secret.encode(), b"nimbus-worker-registration-v1", hashlib.sha256).hexdigest()
if not token:
    sys.exit("Set SECRET_KEY in .env or provide NIMBUS_WORKER_TOKEN before starting the worker.")
os.environ["NIMBUS_WORKER_TOKEN"] = token
sys.argv = [str(root / "backend/scripts/worker_agent.py"), *sys.argv[1:]]
runpy.run_path(str(root / "backend/scripts/worker_agent.py"), run_name="__main__")
