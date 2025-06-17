import pytest
from httpx import AsyncClient, ASGITransport
from main import app
import asyncio

@pytest.mark.asyncio
async def test_task_management():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Submit a task
        resp = await ac.post("/v1/tasks/submit", json={"task_type": "demo", "params": {"foo": "bar"}})
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        task_id = data["task_id"]

        # Poll for status
        for _ in range(5):
            status_resp = await ac.get(f"/v1/tasks/status/{task_id}")
            assert status_resp.status_code == 200
            status_data = status_resp.json()
            if status_data["status"] == "success":
                assert status_data["result"]["task_type"] == "demo"
                assert status_data["result"]["params"] == {"foo": "bar"}
                break
            await asyncio.sleep(1)
        else:
            assert False, "Task did not complete in time"
