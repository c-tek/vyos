import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Mock the vyos_api_call for all tests in this file that might trigger it via endpoints
@pytest.fixture(autouse=True)
def mock_vyos_api_for_integration_tests():
    with patch('vyos.vyos_api_call', new_callable=AsyncMock) as mock_vyos_http:
        # Default success for GET operations (like fetching current config)
        mock_vyos_http.return_value = (True, {"data": {}})
        # More specific mocks can be set up within individual tests if needed
        # e.g., for POST operations that return specific success messages or data
        yield mock_vyos_http

# --- DHCP Pool Endpoint Tests ---
@pytest.mark.asyncio
async def test_create_read_update_delete_dhcp_pool_endpoints(client: TestClient, admin_user_api_key: str, mock_vyos_api_for_integration_tests: AsyncMock):
    headers = {"X-API-Key": admin_user_api_key}
    pool_name = "integrationtestpool"
    pool_data_create = {
        "name": pool_name,
        "network": "172.16.0.0/24",
        "range_start": "172.16.0.100",
        "range_stop": "172.16.0.200",
        "default_router": "172.16.0.1",
        "dns_servers": ["8.8.8.8"]
    }

    # Create
    mock_vyos_api_for_integration_tests.return_value = (True, "DHCP Pool created successfully on VyOS") # Mock for create
    response_create = client.post("/v1/dhcp-pools/", headers=headers, json=pool_data_create)
    assert response_create.status_code == 200
    created_pool = response_create.json()
    assert created_pool["name"] == pool_name
    assert created_pool["default_router"] == "172.16.0.1"
    mock_vyos_api_for_integration_tests.assert_called() # Check VyOS was called
    mock_vyos_api_for_integration_tests.reset_mock()

    # Read (by name)
    response_read = client.get(f"/v1/dhcp-pools/{pool_name}", headers=headers)
    assert response_read.status_code == 200
    assert response_read.json()["network"] == "172.16.0.0/24"

    # Read (all)
    response_read_all = client.get("/v1/dhcp-pools/", headers=headers)
    assert response_read_all.status_code == 200
    assert any(p["name"] == pool_name for p in response_read_all.json())

    # Update
    pool_data_update = {"description": "Updated test pool", "lease_time": 7200}
    mock_vyos_api_for_integration_tests.return_value = (True, "DHCP Pool updated successfully on VyOS") # Mock for update
    response_update = client.put(f"/v1/dhcp-pools/{pool_name}", headers=headers, json=pool_data_update)
    assert response_update.status_code == 200
    updated_pool = response_update.json()
    assert updated_pool["description"] == "Updated test pool"
    assert updated_pool["lease_time"] == 7200
    mock_vyos_api_for_integration_tests.assert_called()
    mock_vyos_api_for_integration_tests.reset_mock()

    # Delete
    mock_vyos_api_for_integration_tests.return_value = (True, "DHCP Pool deleted successfully from VyOS") # Mock for delete
    response_delete = client.delete(f"/v1/dhcp-pools/{pool_name}", headers=headers)
    assert response_delete.status_code == 200 # Assuming 200 with a message, or 204
    assert response_delete.json()["message"].startswith(f"DHCP Pool {pool_name} deleted successfully")
    mock_vyos_api_for_integration_tests.assert_called()

    # Verify Deletion
    response_read_after_delete = client.get(f"/v1/dhcp-pools/{pool_name}", headers=headers)
    assert response_read_after_delete.status_code == 404

# --- Firewall Policy & Rule Endpoint Tests ---
@pytest.mark.asyncio
async def test_create_firewall_policy_with_rules(client: TestClient, admin_user_api_key: str, mock_vyos_api_for_integration_tests: AsyncMock):
    headers = {"X-API-Key": admin_user_api_key}
    policy_name = "INT_FW_POLICY"
    policy_data = {
        "name": policy_name,
        "default_action": "drop",
        "description": "Integration test firewall policy",
        "rules": [
            {
                "rule_number": 10,
                "action": "accept",
                "description": "Allow SSH",
                "protocol": "tcp",
                "destination_port": "22",
                "source_address": "192.168.100.0/24"
            }
        ]
    }
    mock_vyos_api_for_integration_tests.return_value = (True, "Firewall policy created on VyOS")
    response = client.post("/v1/firewall/policies/", headers=headers, json=policy_data)
    assert response.status_code == 200
    created_policy = response.json()
    assert created_policy["name"] == policy_name
    assert len(created_policy["rules"]) == 1
    assert created_policy["rules"][0]["rule_number"] == 10
    mock_vyos_api_for_integration_tests.assert_called()
    policy_id = created_policy["id"]
    rule_id = created_policy["rules"][0]["id"]

    # Add more tests for GET, PUT, DELETE for policies and rules
    # Example: Get the policy
    response_get_policy = client.get(f"/v1/firewall/policies/{policy_id}", headers=headers)
    assert response_get_policy.status_code == 200
    assert response_get_policy.json()["name"] == policy_name

    # Example: Delete the rule
    mock_vyos_api_for_integration_tests.reset_mock()
    mock_vyos_api_for_integration_tests.return_value = (True, "Firewall rule deleted from VyOS")
    response_delete_rule = client.delete(f"/v1/firewall/policies/{policy_id}/rules/{rule_id}", headers=headers)
    assert response_delete_rule.status_code == 204
    mock_vyos_api_for_integration_tests.assert_called()

# --- Static Route Endpoint Tests ---
@pytest.mark.asyncio
async def test_create_read_delete_static_route(client: TestClient, admin_user_api_key: str, mock_vyos_api_for_integration_tests: AsyncMock):
    headers = {"X-API-Key": admin_user_api_key}
    route_data = {
        "destination_network": "10.100.0.0/24",
        "next_hop_address": "172.16.1.254",
        "description": "Integration test static route"
    }
    mock_vyos_api_for_integration_tests.return_value = (True, "Static route created on VyOS")
    response_create = client.post("/v1/static-routes/", headers=headers, json=route_data)
    assert response_create.status_code == 200
    created_route = response_create.json()
    assert created_route["destination_network"] == "10.100.0.0/24"
    route_id = created_route["id"]
    mock_vyos_api_for_integration_tests.assert_called()

    # Read
    response_read = client.get(f"/v1/static-routes/{route_id}", headers=headers)
    assert response_read.status_code == 200
    assert response_read.json()["next_hop_address"] == "172.16.1.254"

    # Delete
    mock_vyos_api_for_integration_tests.reset_mock()
    mock_vyos_api_for_integration_tests.return_value = (True, "Static route deleted from VyOS")
    response_delete = client.delete(f"/v1/static-routes/{route_id}", headers=headers)
    assert response_delete.status_code == 204
    mock_vyos_api_for_integration_tests.assert_called()

# --- VM Provisioning (Simplified Test - Focus on network aspects) ---
@pytest.mark.asyncio
async def test_vm_provision_network_config(client: TestClient, admin_user_api_key: str, mock_vyos_api_for_integration_tests: AsyncMock):
    headers = {"X-API-Key": admin_user_api_key}
    # Create a DHCP pool first for the VM to use
    dhcp_pool_name = "vmprovpool"
    dhcp_data = {"name": dhcp_pool_name, "network": "192.168.77.0/24", "range_start": "192.168.77.10", "range_stop": "192.168.77.20"}
    mock_vyos_api_for_integration_tests.return_value = (True, "DHCP Pool created")
    client.post("/v1/dhcp-pools/", headers=headers, json=dhcp_data)
    mock_vyos_api_for_integration_tests.reset_mock()

    vm_provision_data = {
        "machine_id": "testvm-int-01",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "hostname": "testvm-int-01-host",
        "dhcp_pool_name": dhcp_pool_name, # Use the created pool
        "ports_to_forward": [
            {"port_type": "ssh", "external_port": 2201}
        ]
    }
    # Mock calls for DHCP static mapping and NAT rule creation
    # This might involve multiple calls to vyos_api_call, so a more sophisticated mock might be needed
    # For simplicity, assume one overarching success message or check call count.
    mock_vyos_api_for_integration_tests.return_value = (True, "VM network configured on VyOS")
    response = client.post("/v1/vms/provision", headers=headers, json=vm_provision_data)
    assert response.status_code == 200
    provisioned_data = response.json()
    assert provisioned_data["machine_id"] == "testvm-int-01"
    assert provisioned_data["internal_ip"] is not None # IP should be assigned from pool
    assert len(provisioned_data["ports"]) == 1
    assert provisioned_data["ports"][0]["external_port"] == 2201
    # Check if vyos_api_call was made for DHCP static mapping and NAT
    # Exact number of calls depends on implementation details in crud/routers
    assert mock_vyos_api_for_integration_tests.call_count >= 1 

# Add tests for /vms/decommission, /vms/{machine_id}/status, etc.

def test_dynamic_to_static_provision_success(client: TestClient):
    # Patch get_dhcp_leases to return a known lease
    with patch("vyos_core.get_dhcp_leases", return_value=[("AA:BB:CC:DD:EE:FF", "192.168.1.100")]):
        req = {"mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.100", "description": "Test static mapping"}
        response = client.post("/v1/dhcp/dynamic-to-static", json=req)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["mac"] == req["mac"]
        assert data["ip"] == req["ip"]

def test_dynamic_to_static_provision_not_found(client: TestClient):
    # Patch get_dhcp_leases to return no matching lease
    with patch("vyos_core.get_dhcp_leases", return_value=[("AA:BB:CC:DD:EE:FF", "192.168.1.101")]):
        req = {"mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.100"}
        response = client.post("/v1/dhcp/dynamic-to-static", json=req)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "not found" in data["message"]

# --- VPN Endpoint Tests ---
def test_create_vpn_success(client: TestClient):
    with patch("vyos_core.vyos_api_call", return_value={"result": "ok"}):
        req = {
            "name": "vpn1",
            "type": "ipsec",
            "remote_address": "203.0.113.1",
            "pre_shared_key": "testkey"
        }
        response = client.post("/v1/vpn/create", json=req)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["name"] == req["name"]
        assert data["type"] == req["type"]

def test_create_vpn_failure(client: TestClient):
    with patch("vyos_core.vyos_api_call", side_effect=Exception("VyOS error")):
        req = {
            "name": "vpn2",
            "type": "wireguard",
            "remote_address": "peer1",
            "local_address": "10.0.0.1",
            "public_key": "pubkey",
            "private_key": "privkey",
            "allowed_ips": ["10.0.0.2/32"]
        }
        response = client.post("/v1/vpn/create", json=req)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["name"] == req["name"]
        assert data["type"] == req["type"]
