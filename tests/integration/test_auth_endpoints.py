import pytest
import httpx
from models import User

# Test User Registration and Login
@pytest.mark.asyncio
async def test_create_user_endpoint(async_client: httpx.AsyncClient, admin_user_token: str):
    headers = {"Authorization": f"Bearer {admin_user_token}"}
    user_data = {"username": "newtestuser", "password": "newpassword123", "roles": ["user"]}
    response = await async_client.post("/v1/auth/users/", headers=headers, json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newtestuser"
    assert "user" in data["roles"]

@pytest.mark.asyncio
async def test_login_for_access_token(async_client: httpx.AsyncClient, test_user: User, test_user_credentials):
    login_data = {
        "username": test_user_credentials["username"],
        "password": test_user_credentials["password"],
    }
    response = await async_client.post("/v1/auth/token", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

# Test User API Key Management Endpoints
@pytest.mark.asyncio
async def test_create_list_delete_user_api_key(async_client: httpx.AsyncClient, test_user_token: str):
    headers = {"Authorization": f"Bearer {test_user_token}"}

    # Create API Key
    key_description = "My Test API Key"
    response_create = await async_client.post("/v1/auth/users/me/api-keys/", headers=headers, json={"description": key_description})
    assert response_create.status_code == 200
    created_key_data = response_create.json()
    assert created_key_data["description"] == key_description
    assert "api_key" in created_key_data
    api_key_id = created_key_data["id"]

    # List API Keys
    response_list = await async_client.get("/v1/auth/users/me/api-keys/", headers=headers)
    assert response_list.status_code == 200
    listed_keys_data = response_list.json()
    assert isinstance(listed_keys_data, list)
    assert any(key["id"] == api_key_id and key["description"] == key_description for key in listed_keys_data)

    # Delete API Key
    response_delete = await async_client.delete(f"/v1/auth/users/me/api-keys/{api_key_id}", headers=headers)
    assert response_delete.status_code == 204

    # Verify Deletion (Optional: try to get it or list again)
    response_list_after_delete = await async_client.get("/v1/auth/users/me/api-keys/", headers=headers)
    assert not any(key["id"] == api_key_id for key in response_list_after_delete.json())

# Test Access with API Key
@pytest.mark.asyncio
async def test_access_protected_route_with_api_key(async_client: httpx.AsyncClient, test_user_api_key: str, admin_user_api_key: str):
    # Example: Accessing the "get current user" endpoint which should work with API key auth
    # Note: The /users/me endpoint itself is JWT authenticated. 
    # We need an endpoint that is primarily API key authenticated.
    # Let's assume /v1/dhcp-pools/ is one such endpoint (adjust if not the case)
    
    # First, let's test /v1/auth/users/me/api-keys/ with the API key itself (it should fail as it expects JWT)
    api_key_headers = {"X-API-Key": test_user_api_key}
    response_me_keys = await async_client.get("/v1/auth/users/me/api-keys/", headers=api_key_headers)
    assert response_me_keys.status_code == 401 # Expecting unauthorized as this specific path needs JWT for /me/

    # Let's test an endpoint that IS designed for API Key access, e.g., listing DHCP pools
    # This requires the user associated with test_user_api_key to have permissions for DHCP pools.
    # For simplicity, we'll assume the test_user (non-admin) might get a 403 if only admins can list pools,
    # or an empty list if they can but have none. An admin API key would be better here.

    # Using admin_user_api_key fixture from conftest.py for an admin-privileged action
    admin_api_key_headers = {"X-API-Key": admin_user_api_key}
    response_dhcp = await async_client.get("/v1/dhcp-pools/", headers=admin_api_key_headers)
    # This will depend on whether admin_user has rights and if any pools exist.
    # For now, just check it doesn't give 401 (unauthenticated)
    assert response_dhcp.status_code != 401 
    # A more specific check would be 200, or 403 if permissions are the issue, or 404 if endpoint not found.
    # Assuming it's 200 for a successful list (even if empty)
    assert response_dhcp.status_code == 200 

# Test Role-Based Access Control (RBAC)
@pytest.mark.asyncio
async def test_rbac_admin_endpoint_access(async_client: httpx.AsyncClient, test_user_token: str, admin_user_token: str):
    # Endpoint that requires admin role, e.g., listing all users
    admin_endpoint = "/v1/auth/users/"

    # Try with non-admin user token
    user_headers = {"Authorization": f"Bearer {test_user_token}"}
    response_user_access = await async_client.get(admin_endpoint, headers=user_headers)
    assert response_user_access.status_code == 403  # Forbidden

    # Try with admin user token
    admin_headers = {"Authorization": f"Bearer {admin_user_token}"}
    response_admin_access = await async_client.get(admin_endpoint, headers=admin_headers)
    assert response_admin_access.status_code == 200 # OK

# Add more tests for other auth scenarios: token expiry, invalid tokens, etc.
