# Local scripts

`local.py` manages the Compose stack and a host execution agent. `start_worker.py` loads the local registration credential from the repository `.env` without printing it and launches `backend/scripts/worker_agent.py`.

```sh
python3 scripts/local.py up          # Build/start services, then start the agent
python3 scripts/local.py agent       # Start the agent against an existing local stack
python3 scripts/local.py stop-agent  # Stop its current container and report offline
python3 scripts/local.py down        # Stop the agent and Compose; keep data volumes
```

Runtime PID and logs are stored in the ignored `.nimbus/` directory. The manager verifies the recorded PID belongs to this repository's worker before signalling it. Run these scripts as an ordinary user with access to Docker, and start only one agent per Docker daemon.

For remote workers, run the standard-library-only `backend/scripts/worker_agent.py` directly, supplying a private token file and API URL. See the [README](../README.md#connect-another-machine).
