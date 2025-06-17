import pytest
from httpx import AsyncClient
from main import app
from sqlalchemy.ext.asyncio import AsyncSession
from config import get_async_db
import models
import schemas
import asyncio
import auth

@pytest.mark.asyncio
async def test_hadr_crud_flow(async_client: AsyncClient, test_db_engine):
    # Create first admin user via API (bootstrap)
    admin_payload = {
        "username": "adminuser",
        "password": "adminpassword",
        "roles": ["user"]  # 'admin' will be added automatically
    }
    resp = await async_client.post("/v1/auth/users/", json=admin_payload)
    assert resp.status_code == 201, resp.text
    assert "admin" in resp.json()["roles"]

    # Login as admin to get token
    login_data = {"username": "adminuser", "password": "adminpassword"}
    resp = await async_client.post("/v1/auth/token", data=login_data)
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create HADR config
    payload = {
        "mode": "active",
        "peer_address": "10.0.0.2",
        "failover_state": "healthy",
        "snapshot_info": {"snapshot_id": "snap1"}
    }
    resp = await async_client.post("/v1/hadr/", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    config_id = data["id"]
    assert data["mode"] == "active"
    assert data["peer_address"] == "10.0.0.2"

    # Get HADR config
    resp = await async_client.get("/v1/hadr/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == config_id

    # Update HADR config
    update_payload = {"mode": "standby", "failover_state": "degraded"}
    resp = await async_client.put(f"/v1/hadr/{config_id}", json=update_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "standby"
    assert data["failover_state"] == "degraded"

    # Delete HADR config
    resp = await async_client.delete(f"/v1/hadr/{config_id}", headers=headers)
    assert resp.status_code == 204

    # Confirm deletion
    resp = await async_client.get("/v1/hadr/", headers=headers)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_hadr_status_and_failover(async_client: AsyncClient, test_db_engine):
    # Create admin and login
    admin_payload = {"username": "adminuser2", "password": "adminpassword2", "roles": ["user"]}
    resp = await async_client.post("/v1/auth/users/", json=admin_payload)
    assert resp.status_code == 201
    login_data = {"username": "adminuser2", "password": "adminpassword2"}
    resp = await async_client.post("/v1/auth/token", data=login_data)
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Create HADR config
    payload = {"mode": "active", "peer_address": "10.0.0.3", "failover_state": "healthy", "snapshot_info": {"snapshot_id": "snap2"}}
    resp = await async_client.post("/v1/hadr/", json=payload, headers=headers)
    assert resp.status_code == 201
    # Check status
    resp = await async_client.get("/v1/hadr/status", headers=headers)
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["mode"] == "active"
    assert status_data["failover_state"] == "healthy"
    # Trigger failover
    resp = await async_client.post("/v1/hadr/failover", headers=headers)
    assert resp.status_code == 200
    failover_data = resp.json()
    assert failover_data["new_state"] == "failed_over"
    # Status should now reflect failover
    resp = await async_client.get("/v1/hadr/status", headers=headers)
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["failover_state"] == "failed_over"
