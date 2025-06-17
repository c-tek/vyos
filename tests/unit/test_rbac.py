import pytest
from fastapi.testclient import TestClient
from main import app
from models import create_db_tables
from config import engine

@pytest.fixture(autouse=True, scope="session")
def setup_db():
    create_db_tables(engine)

def test_create_and_list_roles():
    client = TestClient(app)
    # Create a role
    resp = client.post("/v1/rbac/roles", json={"name": "testrole", "description": "A test role", "permissions": ["network.read"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "testrole"
    # List roles
    resp = client.get("/v1/rbac/roles")
    assert resp.status_code == 200
    roles = resp.json()
    assert any(r["name"] == "testrole" for r in roles)
