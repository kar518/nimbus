import asyncio
import base64
import uuid
from datetime import timedelta

import pytest

from app.core.security import worker_bootstrap_token
from app.models.job import Job
from app.models.worker import GPUWorker
from app.services.job_service import now

PREFIX = "/api/v1"


async def submit(admin, **overrides):
    response = await admin.post(PREFIX + "/jobs", json={"title": "Test workload", **overrides})
    assert response.status_code == 201, response.text
    return response.json()


async def claim(admin, worker, schedule):
    info, headers = worker
    await schedule()
    assignment = (
        await admin.get(f"{PREFIX}/workers/{info['id']}/assignment", headers=headers)
    ).json()
    assert assignment
    job_id = assignment["job"]["id"]
    path = f"{PREFIX}/workers/{info['id']}/jobs/{job_id}"
    lease = {"execution_token": assignment["execution_token"]}
    response = await admin.post(path + "/claim", headers=headers, json=lease)
    assert response.status_code == 200, response.text
    return path, lease, headers, job_id


@pytest.mark.asyncio
async def test_authentication_and_first_admin(client):
    assert (await client.get(PREFIX + "/jobs")).status_code == 401
    setup = await client.post(
        PREFIX + "/auth/setup", json={"username": "owner", "password": "strong-password-123"}
    )
    assert setup.status_code == 200
    assert "HttpOnly" in setup.headers["set-cookie"]
    assert (
        await client.post(
            PREFIX + "/auth/setup", json={"username": "another", "password": "strong-password-123"}
        )
    ).status_code == 409
    await client.post(PREFIX + "/auth/logout")
    assert (await client.get(PREFIX + "/jobs")).status_code == 401
    assert (
        await client.post(
            PREFIX + "/auth/login", json={"username": "owner", "password": "wrong-password-123"}
        )
    ).status_code == 401
    assert (
        await client.post(
            PREFIX + "/auth/login", json={"username": "owner", "password": "strong-password-123"}
        )
    ).status_code == 200


@pytest.mark.asyncio
async def test_real_lifecycle_logs_and_artifacts(admin, worker, schedule):
    job = await submit(admin)
    path, lease, headers, job_id = await claim(admin, worker, schedule)
    assert job_id == job["id"]
    for _ in range(2):
        result = await admin.post(
            path + "/logs", headers=headers, json={**lease, "offset": 0, "text": "Hello Nimbus\n"}
        )
        assert result.status_code == 200
    assert (await admin.get(f"{PREFIX}/jobs/{job_id}/logs")).json()["text"] == "Hello Nimbus\n"
    payload = {
        **lease,
        "exit_code": 0,
        "artifacts": [
            {"filename": "result.json", "content_base64": base64.b64encode(b'{"ok":true}').decode()}
        ],
    }
    for _ in range(2):
        result = await admin.post(path + "/finish", headers=headers, json=payload)
        assert result.status_code == 200
        assert result.json()["status"] == "COMPLETED"
    outputs = (await admin.get(f"{PREFIX}/jobs/{job_id}/artifacts")).json()
    assert len(outputs) == 1
    result = await admin.get(f"{PREFIX}/jobs/{job_id}/artifacts/{outputs[0]['id']}")
    assert result.content == b'{"ok":true}'
    assert (await admin.get(PREFIX + "/workers")).json()[0]["status"] == "IDLE"


@pytest.mark.asyncio
async def test_concurrent_schedulers_do_not_duplicate_assignment(admin, worker, schedule):
    for index in range(3):
        await submit(admin, title=f"Job {index}", priority=index)
    first, second = await asyncio.gather(schedule(), schedule())
    assert len(first) + len(second) == 1
    jobs = (await admin.get(PREFIX + "/jobs")).json()
    assert sum(job["status"] == "ASSIGNED" for job in jobs) == 1
    assert next(job for job in jobs if job["status"] == "ASSIGNED")["title"] == "Job 2"


@pytest.mark.asyncio
async def test_resource_admission_and_queue_reason(admin, worker, schedule):
    oversized = await submit(admin, cpu_request="3", gpu_memory_request=1024)
    small = await submit(admin, title="Fits the worker")
    await schedule()
    assert (await admin.get(f"{PREFIX}/jobs/{oversized['id']}")).json()["status"] == "QUEUED"
    assert (
        "enough requested"
        in (await admin.get(f"{PREFIX}/jobs/{oversized['id']}")).json()["waiting_reason"]
    )
    assert (await admin.get(f"{PREFIX}/jobs/{small['id']}")).json()["status"] == "ASSIGNED"


@pytest.mark.asyncio
async def test_running_cancellation_holds_worker_until_confirmation(admin, worker, schedule):
    job = await submit(admin)
    path, lease, headers, _ = await claim(admin, worker, schedule)
    result = await admin.post(f"{PREFIX}/jobs/{job['id']}/cancel")
    assert result.json()["cancel_requested"] is True
    assert result.json()["status"] == "RUNNING"
    assert (await admin.get(PREFIX + "/workers")).json()[0]["status"] == "BUSY"
    assert (await admin.post(path + "/control", headers=headers, json=lease)).json()[
        "cancel"
    ] is True
    result = await admin.post(
        path + "/finish",
        headers=headers,
        json={**lease, "exit_code": 137, "reason": "Cancelled by operator."},
    )
    assert result.json()["status"] == "CANCELLED"
    assert (await admin.get(PREFIX + "/workers")).json()[0]["current_job"] is None


@pytest.mark.asyncio
async def test_queued_cancellation_and_retry_preserve_history(admin):
    job = await submit(admin)
    assert (await admin.post(f"{PREFIX}/jobs/{job['id']}/cancel")).json()["status"] == "CANCELLED"
    retry = await admin.post(f"{PREFIX}/jobs/{job['id']}/retry")
    assert retry.status_code == 201
    assert retry.json()["id"] != job["id"]
    assert retry.json()["retry_of"] == job["id"]
    assert retry.json()["status"] == "QUEUED"
    assert (await admin.post(f"{PREFIX}/jobs/{retry.json()['id']}/retry")).status_code == 409


@pytest.mark.asyncio
async def test_stale_worker_fails_job_and_rejects_late_logs(
    admin, worker, schedule, session_factory
):
    await submit(admin)
    path, lease, headers, job_id = await claim(admin, worker, schedule)
    async with session_factory() as db:
        machine = await db.get(GPUWorker, uuid.UUID(worker[0]["id"]))
        machine.last_heartbeat = now() - timedelta(seconds=120)
        await db.commit()
    await schedule()
    assert (await admin.get(f"{PREFIX}/jobs/{job_id}")).json()["status"] == "FAILED"
    assert (
        await admin.post(
            path + "/logs", headers=headers, json={**lease, "offset": 0, "text": "late"}
        )
    ).status_code == 409


@pytest.mark.asyncio
async def test_assignment_can_only_be_claimed_once(admin, worker, schedule):
    await submit(admin)
    path, lease, headers, _ = await claim(admin, worker, schedule)
    assert (await admin.post(path + "/claim", headers=headers, json=lease)).status_code == 409
    assert (
        await admin.post(
            path + "/finish",
            headers=headers,
            json={"execution_token": str(uuid.uuid4()), "exit_code": 0},
        )
    ).status_code == 409
    assert (await admin.post(path + "/finish", json={**lease, "exit_code": 0})).status_code == 401


@pytest.mark.asyncio
async def test_member_cannot_read_or_cancel_another_users_job(admin):
    job = await submit(admin)
    response = await admin.post(
        PREFIX + "/auth/users", json={"username": "member", "password": "member-password-123"}
    )
    assert response.status_code == 201
    await admin.post(PREFIX + "/auth/logout")
    await admin.post(
        PREFIX + "/auth/login", json={"username": "member", "password": "member-password-123"}
    )
    assert (await admin.get(PREFIX + "/jobs")).json() == []
    assert (await admin.get(f"{PREFIX}/jobs/{job['id']}")).status_code == 404
    assert (await admin.post(f"{PREFIX}/jobs/{job['id']}/cancel")).status_code == 404
    assert (await admin.get(PREFIX + "/auth/worker-token")).status_code == 403
    own = await submit(admin)
    assert (await admin.get(f"{PREFIX}/jobs/{own['id']}")).status_code == 200


@pytest.mark.asyncio
async def test_validation_and_origin_protection(admin):
    assert (
        await admin.post(PREFIX + "/jobs", json={"title": " ", "cpu_request": 0})
    ).status_code == 422
    assert (
        await admin.post(PREFIX + "/jobs", json={"title": "x", "owner_id": str(uuid.uuid4())})
    ).status_code == 422
    result = await admin.post(
        PREFIX + "/jobs", headers={"Origin": "https://untrusted.example"}, json={"title": "x"}
    )
    assert result.status_code == 403
    result = await admin.get(PREFIX + "/health", headers={"Origin": "http://localhost:5173"})
    assert result.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.asyncio
async def test_worker_drain_and_duplicate_registration(admin, worker, schedule):
    worker_id = worker[0]["id"]
    await admin.post(f"{PREFIX}/workers/{worker_id}/drain", json={"draining": True})
    job = await submit(admin)
    assert await schedule() == []
    await admin.post(f"{PREFIX}/workers/{worker_id}/drain", json={"draining": False})
    assert len(await schedule()) == 1
    duplicate = await admin.post(
        PREFIX + "/workers/register",
        headers={"Authorization": "Bearer " + worker_bootstrap_token()},
        json={"name": "test-worker"},
    )
    assert duplicate.status_code == 409
    assert (await admin.get(f"{PREFIX}/jobs/{job['id']}")).json()["status"] == "ASSIGNED"


@pytest.mark.asyncio
async def test_timeout_recovery_and_failure_reason(admin, worker, schedule, session_factory):
    await submit(admin, timeout_seconds=1)
    _, _, _, job_id = await claim(admin, worker, schedule)
    async with session_factory() as db:
        job = await db.get(Job, uuid.UUID(job_id))
        job.started_at = now() - timedelta(seconds=200)
        await db.commit()
    await schedule()
    recovered = (await admin.get(f"{PREFIX}/jobs/{job_id}")).json()
    assert recovered["status"] == "FAILED"
    assert "timeout" in recovered["failure_reason"]


@pytest.mark.asyncio
async def test_literal_search_and_history_filter(admin):
    await submit(admin, title="model_eval")
    second = await submit(admin, title="modelXeval")
    await admin.post(f"{PREFIX}/jobs/{second['id']}/cancel")
    matches = (await admin.get(PREFIX + "/jobs", params={"q": "model_"})).json()
    assert [job["title"] for job in matches] == ["model_eval"]
    history = (await admin.get(PREFIX + "/jobs", params={"history": True})).json()
    assert [job["id"] for job in history] == [second["id"]]
    summary = (await admin.get(PREFIX + "/jobs/summary")).json()
    assert summary["total"] == 2
    assert summary["success_rate"] is None


@pytest.mark.asyncio
async def test_old_agent_credentials_are_revoked_on_reconnection(admin, worker):
    info, old_headers = worker
    response = await admin.post(f"{PREFIX}/workers/{info['id']}/offline", headers=old_headers)
    assert response.status_code == 200
    response = await admin.post(
        PREFIX + "/workers/register",
        headers={"Authorization": "Bearer " + worker_bootstrap_token()},
        json={"name": "test-worker", "cpu_capacity": 2, "memory_capacity_mb": 2048},
    )
    assert response.status_code == 201
    assert response.json()["worker"]["id"] == info["id"]
    assert (
        await admin.post(f"{PREFIX}/workers/{info['id']}/heartbeat", headers=old_headers, json={})
    ).status_code == 401
    new_headers = {"Authorization": "Bearer " + response.json()["token"]}
    assert (
        await admin.post(f"{PREFIX}/workers/{info['id']}/heartbeat", headers=new_headers, json={})
    ).status_code == 200
