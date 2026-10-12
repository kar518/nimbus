# Verification

Validation performed against the local Nimbus stack on 11–12 October 2026.

## Automated checks

- 15 backend integration tests pass against disposable PostgreSQL databases migrated from empty. They cover authentication, ownership, concurrent scheduling, capacity/priority, execution leases, log deduplication, artifacts, cancellation, retry, heartbeat/timeout recovery, draining, search/summary, and worker session replacement.
- Three frontend workflow tests cover executable submission, malformed command rejection, and pending cancellation while a worker is still stopping.
- Backend Ruff lint and strict mypy checks, frontend ESLint, TypeScript compilation, and the frontend production build pass.
- Runtime Python dependency audit and the full npm dependency audit report no known vulnerabilities at verification time. This is a dependency check, not a complete security assessment.

## Actual container execution

The host worker executed real Docker containers for these scenarios:

| Scenario | Observed result |
| --- | --- |
| Successful command | Completed with exit code 0; stdout retained; `result.json` downloaded and parsed |
| Intentional exit code 7 | Failed with exit code 7 |
| Two-second timeout | Container terminated; failed with timeout reason |
| Cancellation while running | Container terminated; cancelled only after agent confirmation |
| Retry | Separate linked job executed and completed |
| GPU request on CPU-only host | Remained queued with a capacity explanation; never assigned |

Execution test containers were removed. Verification workloads remain in history with descriptive titles; original legacy jobs and workers were preserved. The temporary verification account is removed after browser checks so the first administrator can choose their own credentials.

Browser checks include submitting the built-in Hello Nimbus example, viewing its actual outcome, navigating the workspace, and checking a 375-pixel mobile viewport. Screenshots are in `docs/screenshots/`. Both standalone production images built successfully. A temporary nginx container passed SPA fallback, authenticated API, dependency readiness, security header, and WebSocket event checks against the local backend.

## Boundaries

CPU execution was tested on Docker Desktop with an 8-core, approximately 3.6 GiB advertised worker. No NVIDIA hardware was available, so real GPU execution remains unverified. Public HTTPS deployment, high-load behavior, large artifact storage, automated backup/restore, and multi-host fault injection were not validated. CI configuration is included; a hosted CI run requires pushing the changes.
