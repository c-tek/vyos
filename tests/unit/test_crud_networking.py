import pytest
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from schemas import DHCPPoolCreate, DHCPPoolUpdate, VMProvisionRequest, VMNetworkConfigCreate, VMPortRuleCreate, FirewallPolicyCreate, FirewallRuleCreate, StaticRouteCreate
from crud import (
    create_dhcp_pool, get_dhcp_pool_by_name, get_all_dhcp_pools, update_dhcp_pool, delete_dhcp_pool,
    create_firewall_policy, get_firewall_policy, get_all_firewall_policies_for_user, update_firewall_policy, delete_firewall_policy,
    create_firewall_rule, get_firewall_rule, get_firewall_rules_for_policy, update_firewall_rule, delete_firewall_rule,
    create_static_route, get_static_route, get_static_routes_by_user, update_static_route, delete_static_route,
    get_all_dhcp_pools, create_vm, add_port_rule,
)
from models import User, DHCPPool, VMNetworkConfig, VMPortRule, PortType, PortStatus, FirewallPolicy, FirewallRule, StaticRoute
from schemas import DHCPPoolCreate, DHCPPoolUpdate, VMNetworkConfigCreate, VMPortRuleCreate, FirewallPolicyCreate, FirewallRuleCreate, StaticRouteCreate
from utils import hash_password
from exceptions import ResourceAllocationError, VyOSAPIError
from vyos_core import vyos_api_call # To mock, changed from vyos to vyos_core
import crud_quota
from models import Quota

# Mock vyos_api_call for all CRUD tests that interact with VyOS
@pytest.fixture(autouse=True)
def mock_vyos_interaction():
    with patch('crud.vyos_api_call', new_callable=AsyncMock) as mock_vyos:
        mock_vyos.return_value = (True, "Mocked VyOS success") # Default success
        yield mock_vyos

# --- DHCP Pool Tests --- 
@pytest.mark.asyncio
async def test_create_and_get_dhcp_pool(db_session: AsyncSession, admin_user: User, mock_vyos_interaction: AsyncMock):
    pool_in = DHCPPoolCreate(name="testpool1", network="192.168.1.0/24", range_start="192.168.1.100", range_stop="192.168.1.200")
    db_pool = await create_dhcp_pool(db_session, pool_in=pool_in, user_id=admin_user.id)
    
    assert db_pool.name == "testpool1"
    assert db_pool.network == "192.168.1.0/24"
    mock_vyos_interaction.assert_called_once() # Check that VyOS interaction was attempted

    retrieved_pool = await get_dhcp_pool_by_name(db_session, name="testpool1")
    assert retrieved_pool is not None
    assert retrieved_pool.id == db_pool.id

@pytest.mark.asyncio
async def test_update_dhcp_pool(db_session: AsyncSession, admin_user: User, mock_vyos_interaction: AsyncMock):
    pool_in = DHCPPoolCreate(name="updatepool", network="192.168.2.0/24", range_start="192.168.2.100", range_stop="192.168.2.200")
    db_pool = await create_dhcp_pool(db_session, pool_in=pool_in, user_id=admin_user.id)
    mock_vyos_interaction.reset_mock() # Reset after creation

    update_data = DHCPPoolUpdate(range_start="192.168.2.150", description="Updated pool")
    updated_pool = await update_dhcp_pool(db_session, db_pool=db_pool, pool_in=update_data)
    
    assert updated_pool is not None
    assert updated_pool.range_start == "192.168.2.150"
    assert updated_pool.description == "Updated pool"
    mock_vyos_interaction.assert_called_once()

@pytest.mark.asyncio
async def test_delete_dhcp_pool(db_session: AsyncSession, admin_user: User, mock_vyos_interaction: AsyncMock):
    pool_in = DHCPPoolCreate(name="deletepool", network="192.168.3.0/24", range_start="192.168.3.100", range_stop="192.168.3.200")
    db_pool = await create_dhcp_pool(db_session, pool_in=pool_in, user_id=admin_user.id)
    mock_vyos_interaction.reset_mock()
    pool_id = db_pool.id

    deleted_pool = await delete_dhcp_pool(db_session, db_pool=db_pool)
    assert deleted_pool is not None
    assert deleted_pool.id == pool_id
    mock_vyos_interaction.assert_called_once()

    retrieved_pool = await get_dhcp_pool_by_name(db_session, name="deletepool")
    assert retrieved_pool is None

# --- VM Network Config & Port Rule Tests (Simplified as they are closely tied to provisioning logic) ---
@pytest.mark.asyncio
async def test_create_vm_port_rule(db_session: AsyncSession, admin_user: User, mock_vyos_interaction: AsyncMock):
    vm_config_in = VMNetworkConfigCreate(machine_id="testvm_pr", internal_ip="192.168.1.11", mac_address="00:11:22:33:44:66", dhcp_pool_id=None, hostname=None)
    db_vm_config = await create_vm(db_session, machine_id=vm_config_in.machine_id, mac_address=vm_config_in.mac_address, internal_ip=vm_config_in.internal_ip, dhcp_pool_id=vm_config_in.dhcp_pool_id, hostname=vm_config_in.hostname)

    port_rule_in = VMPortRuleCreate(vm_id=db_vm_config.id, port_type="ssh", external_port=2222, nat_rule_number=100)
    db_port_rule = await add_port_rule(db_session, db_vm_config, PortType.ssh, port_rule_in.external_port, port_rule_in.nat_rule_number, PortStatus.enabled)
    assert db_port_rule.port_type == PortType.ssh
    assert db_port_rule.external_port == 2222
    # create_vm_port_rule itself doesn't call vyos, it's usually part of a larger operation
    # mock_vyos_interaction.assert_called_once() # This would fail as written

# --- Firewall Policy Tests --- 
@pytest.mark.asyncio
async def test_create_and_get_firewall_policy(db_session: AsyncSession, admin_user: User, mock_vyos_interaction: AsyncMock):
    policy_in = FirewallPolicyCreate(name="FW_POLICY_TEST", default_action="accept", user_id=admin_user.id)
    db_policy = await create_firewall_policy(db_session, policy_in=policy_in)
    
    assert db_policy.name == "FW_POLICY_TEST"
    assert db_policy.default_action == "accept"
    mock_vyos_interaction.assert_called_once()

    retrieved_policy = await get_firewall_policy(db_session, policy_id=db_policy.id, user_id=admin_user.id)
    assert retrieved_policy is not None
    assert retrieved_policy.id == db_policy.id

# --- Firewall Rule Tests --- 
@pytest.mark.asyncio
async def test_create_and_get_firewall_rule(db_session: AsyncSession, admin_user: User, mock_vyos_interaction: AsyncMock):
    policy_in = FirewallPolicyCreate(name="FW_POLICY_FOR_RULE_TEST", default_action="drop", user_id=admin_user.id)
    db_policy = await create_firewall_policy(db_session, policy_in=policy_in)
    mock_vyos_interaction.reset_mock()

    rule_in = FirewallRuleCreate(policy_id=db_policy.id, rule_number=10, action="accept", source_address="any")
    db_rule = await create_firewall_rule(db_session, rule_in=rule_in, policy_name=db_policy.name)
    
    assert db_rule.rule_number == 10
    assert db_rule.action == "accept"
    mock_vyos_interaction.assert_called_once()

    retrieved_rule = await get_firewall_rule(db_session, rule_id=db_rule.id, policy_id=db_policy.id, user_id=admin_user.id)
    assert retrieved_rule is not None
    assert retrieved_rule.id == db_rule.id

# --- Static Route Tests --- 
@pytest.mark.asyncio
async def test_create_and_get_static_route(db_session: AsyncSession, admin_user: User, mock_vyos_interaction: AsyncMock):
    route_in = StaticRouteCreate(destination_network="10.0.1.0/24", next_hop_address="192.168.1.254", user_id=admin_user.id)
    db_route = await create_static_route(db_session, route_in=route_in)
    
    assert db_route.destination_network == "10.0.1.0/24"
    assert db_route.next_hop_address == "192.168.1.254"
    mock_vyos_interaction.assert_called_once()

    retrieved_route = await get_static_route(db_session, route_id=db_route.id, user_id=admin_user.id)
    assert retrieved_route is not None
    assert retrieved_route.id == db_route.id

# Add more tests for get_all, update, delete for each CRUD section
# Example for DHCP pools get_all:
@pytest.mark.asyncio
async def test_get_dhcp_pools_crud(db_session: AsyncSession, admin_user: User, mock_vyos_interaction: AsyncMock):
    await create_dhcp_pool(db_session, pool_in=DHCPPoolCreate(name="pool_a", network="10.0.1.0/24", range_start="10.0.1.10", range_stop="10.0.1.20"), user_id=admin_user.id)
    await create_dhcp_pool(db_session, pool_in=DHCPPoolCreate(name="pool_b", network="10.0.2.0/24", range_start="10.0.2.10", range_stop="10.0.2.20"), user_id=admin_user.id)
    
    pools = await get_all_dhcp_pools(db_session, skip=0, limit=10)
    assert len(pools) >= 2
    pool_names = [p.name for p in pools]
    assert "pool_a" in pool_names
    assert "pool_b" in pool_names

@pytest.mark.asyncio
async def test_vm_quota_enforcement(db_session: AsyncSession, admin_user):
    admin = await admin_user
    # Set quota for VMs to 2
    quota = await crud_quota.create_quota(db_session, user_id=admin.id, resource_type="vm", limit=2, usage=0)
    # Create two VMs (should succeed)
    for i in range(2):
        vm_name = f"quota-vm-{i}"
        vm = await create_vm(db_session, machine_id=vm_name, mac_address=f"00:11:22:33:44:{i:02x}", internal_ip=f"192.168.1.{10+i}", user_id=admin.id)
        assert vm.machine_id == vm_name
    # Third VM should fail
    with pytest.raises(Exception) as excinfo:
        await create_vm(db_session, machine_id="quota-vm-2", mac_address="00:11:22:33:44:ff", internal_ip="192.168.1.99", user_id=admin.id)
    assert "Quota exceeded" in str(excinfo.value)

# Remember to test failure cases, e.g., deleting a non-existent item, or creating with duplicate names where unique=True
