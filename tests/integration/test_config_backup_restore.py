import pytest
from httpx import AsyncClient
from httpx import ASGITransport
from main import app

@pytest.mark.asyncio
async def test_config_backup_and_restore(monkeypatch):
    # Mock backup_config to return a fake config string
    async def mock_backup_config():
        return "fake-vyos-config-content"
    # Mock restore_config to return a success message
    async def mock_restore_config(backup_content):
        assert backup_content == "fake-vyos-config-content"
        return "VyOS config restored successfully."

    import routers.__init__ as routers_init
    monkeypatch.setattr(routers_init, "backup_config", mock_backup_config)
    monkeypatch.setattr(routers_init, "restore_config", mock_restore_config)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test backup endpoint
        backup_resp = await ac.post("/v1/config/backup")
        assert backup_resp.status_code == 200
        backup_data = backup_resp.json()
        assert backup_data["status"] == "success"
        assert backup_data["backup"] == "fake-vyos-config-content"

        # Test restore endpoint
        restore_resp = await ac.post("/v1/config/restore", json={"backup_content": "fake-vyos-config-content"})
        assert restore_resp.status_code == 200
        restore_data = restore_resp.json()
        assert restore_data["status"] == "success"
        assert restore_data["message"] == "VyOS config restored successfully."
