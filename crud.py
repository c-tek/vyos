from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import DHCPPool, VMNetworkConfig, VMPortRule, PortType, PortStatus, User, APIKey, FirewallPolicy, FirewallRule, StaticRoute, ChangeJournal
from schemas import UserCreate, UserUpdate, FirewallPolicyCreate, FirewallPolicyUpdate, FirewallRuleCreate, FirewallRuleUpdate, StaticRouteCreate, StaticRouteUpdate, ChangeJournalCreate
from utils import hash_password, audit_log_action
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
import logging
from config import SessionLocal, AsyncSessionLocal, get_async_db
from exceptions import ResourceAllocationError, VyOSAPIError
from vyos_core import vyos_api_call, generate_firewall_policy_commands, generate_firewall_rule_commands, generate_static_route_vyos_commands
from fastapi import HTTPException, status

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Utility: shared DB session dependency (original sync version, might be deprecated or used for sync-specific tasks)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Use string type hints for all model references in function signatures
async def get_vm_by_machine_id(db: AsyncSession, machine_id: str) -> 'Optional[VMNetworkConfig]':
    result = await db.execute(select(VMNetworkConfig).filter(VMNetworkConfig.machine_id == machine_id))
    return result.scalars().first()

async def get_dhcp_pool_by_id(db: AsyncSession, pool_id: int) -> 'Optional[DHCPPool]':
    result = await db.execute(select(DHCPool).filter(DHCPool.id == pool_id))
    return result.scalars().first()

async def get_dhcp_pool_by_name(db: AsyncSession, name: str) -> 'Optional[DHCPPool]':
    result = await db.execute(select(DHCPool).filter(DHCPool.name == name))
    return result.scalars().first()

async def create_dhcp_pool(db: AsyncSession, name: str, subnet: str, ip_range_start: str, ip_range_end: str, gateway: Optional[str] = None, dns_servers: Optional[str] = None, domain_name: Optional[str] = None, lease_time: Optional[int] = 86400) -> 'DHCPPool':
    pool = DHCPPool(
        name=name,
        subnet=subnet,
        ip_range_start=ip_range_start,
        ip_range_end=ip_range_end,
        gateway=gateway,
        dns_servers=dns_servers,
        domain_name=domain_name,
        lease_time=lease_time,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(pool)
    await db.commit()
    await db.refresh(pool)
    audit_log_action(user="system", action="create_dhcp_pool", result="success", details={"name": name, "subnet": subnet})
    return pool

async def get_all_dhcp_pools(db: AsyncSession) -> 'List[DHCPPool]':
    result = await db.execute(select(DHCPool))
    return result.scalars().all()

async def update_dhcp_pool(db: AsyncSession, pool: 'DHCPPool', name: Optional[str] = None, subnet: Optional[str] = None, ip_range_start: Optional[str] = None, ip_range_end: Optional[str] = None, gateway: Optional[str] = None, dns_servers: Optional[str] = None, domain_name: Optional[str] = None, lease_time: Optional[int] = None, is_active: Optional[bool] = None) -> 'DHCPPool':
    if name is not None:
        pool.name = name
    if subnet is not None:
        pool.subnet = subnet
    if ip_range_start is not None:
        pool.ip_range_start = ip_range_start
    if ip_range_end is not None:
        pool.ip_range_end = ip_range_end
    if gateway is not None:
        pool.gateway = gateway
    if dns_servers is not None:
        pool.dns_servers = dns_servers
    if domain_name is not None:
        pool.domain_name = domain_name
    if lease_time is not None:
        pool.lease_time = lease_time
    if is_active is not None:
        pool.is_active = is_active
    pool.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(pool)
    return pool

async def is_dhcp_pool_in_use(db: AsyncSession, pool_id: int) -> bool:
    """Checks if a DHCP pool is currently associated with any VMNetworkConfig."""
    stmt = select(VMNetworkConfig.id).filter(VMNetworkConfig.dhcp_pool_id == pool_id).limit(1)
    result = await db.execute(stmt)
    return result.scalars().first() is not None

async def delete_dhcp_pool(db: AsyncSession, pool: 'DHCPPool'):
    """Deletes a DHCP pool from the database. Assumes usage check has been performed by the caller."""
    pool_name = pool.name # For logging
    pool_id = pool.id # For logging
    await db.delete(pool)
    await db.commit()
    logger.info(f"DHCP Pool {pool_name} (ID: {pool_id}) deleted from database successfully.")

async def create_vm(db: AsyncSession, machine_id: str, mac_address: str, internal_ip: Optional[str] = None, dhcp_pool_id: Optional[int] = None, hostname: Optional[str] = None, user_id: Optional[int] = None) -> VMNetworkConfig:
    # Quota enforcement: Only if user_id is provided
    if user_id is not None:
        from crud_quota import get_quota, update_quota
        quota = await get_quota(db, user_id=user_id, resource_type="vm")
        if quota and quota.limit is not None:
            if quota.usage >= quota.limit:
                raise Exception(f"Quota exceeded: limit={quota.limit}, usage={quota.usage}")
    
    if not internal_ip and not dhcp_pool_id:
        raise ValueError("Either internal_ip or dhcp_pool_id must be provided.")
    if internal_ip and dhcp_pool_id:
        pass

    vm = VMNetworkConfig(
        machine_id=machine_id,
        mac_address=mac_address,
        internal_ip=internal_ip, # Can be None if using DHCP pool for IP
        dhcp_pool_id=dhcp_pool_id,
        hostname=hostname,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(vm)
    await db.commit()
    await db.refresh(vm)

    # Increment quota usage after successful creation
    if user_id is not None and quota:
        await update_quota(db, quota, usage=quota.usage + 1)

    # After successful creation, log to journal
    from crud_journal import create_journal_entry
    await create_journal_entry(db, ChangeJournalCreate(
        user_id=user_id,
        resource_type="vm",
        resource_id=vm.machine_id,
        operation="create",
        before=None,
        after={
            "machine_id": vm.machine_id,
            "mac_address": vm.mac_address,
            "internal_ip": vm.internal_ip,
            "dhcp_pool_id": vm.dhcp_pool_id,
            "hostname": vm.hostname
        },
        comment="VM created"
    ))
    return vm

async def add_port_rule(db: AsyncSession, vm: VMNetworkConfig, port_type: PortType, external_port: int, nat_rule_number: int, status: PortStatus = PortStatus.enabled) -> VMPortRule:
    rule = VMPortRule(
        vm_id=vm.id, # Ensure vm_id is used if vm object is not directly linkable before commit in async
        port_type=port_type,
        external_port=external_port,
        nat_rule_number=nat_rule_number,
        status=status
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    # If vm object was passed and relationship is set up, rule.vm = vm might be needed
    # or ensure vm object is refreshed if rule.vm is accessed later.
    # For now, assuming vm_id is sufficient for linking.
    return rule

async def get_port_rule_by_vm_and_type(db: AsyncSession, vm_id: int, port_type: PortType) -> Optional[VMPortRule]:
    result = await db.execute(
        select(VMPortRule).filter_by(vm_id=vm_id, port_type=port_type)
    )
    return result.scalars().first()

async def set_port_status(db: AsyncSession, vm: VMNetworkConfig, port_type: PortType, status: PortStatus):
    # Assuming vm object has its ID populated
    rule = await get_port_rule_by_vm_and_type(db, vm.id, port_type) # Use the new helper
    if rule:
        rule.status = status
        # To update vm.updated_at, we might need to fetch vm again or ensure it's part of the session
        # For now, focusing on port rule. If VM's updated_at is critical, it needs explicit update.
        # vm_instance = await db.get(VMNetworkConfig, vm.id) # Example if needed
        # if vm_instance:
        #     vm_instance.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(rule)
    return rule
    
async def delete_port_rule_by_id(db: AsyncSession, rule_id: int):
    rule = await db.get(VMPortRule, rule_id)
    if rule:
        await db.delete(rule)
        await db.commit()

async def get_vm_ports_status(db: AsyncSession, vm: VMNetworkConfig) -> Dict[str, Dict[str, Any]]:
    # Assuming vm object has its ID populated
    result = await db.execute(select(VMPortRule).filter_by(vm_id=vm.id))
    rules = result.scalars().all()
    ports = {}
    for r in rules:
        ports[r.port_type.value] = {
            "status": r.status.value,
            "external_port": r.external_port,
            "nat_rule_number": r.nat_rule_number
        }
    # Ensure all port types are present
    for p_type in PortType: # Iterate over Enum members
        p_val = p_type.value
        if p_val not in ports:
            ports[p_val] = {"status": "not_active", "external_port": None, "nat_rule_number": None}
    return ports

async def get_all_vms_status(db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(select(VMNetworkConfig))
    vms = result.scalars().all()
    response_data = []
    for vm_instance in vms:
        ports_status = await get_vm_ports_status(db, vm_instance)
        response_data.append({
            "machine_id": vm_instance.machine_id,
            "internal_ip": vm_instance.internal_ip,
            "ports": ports_status
        })
    return response_data

def get_configured_ip_range() -> Tuple[str, int, int]:
    # Example: get from environment or config file
    import os
    base = os.getenv("VYOS_LAN_BASE", "192.168.64.")
    start = int(os.getenv("VYOS_LAN_START", 100))
    end = int(os.getenv("VYOS_LAN_END", 199))
    return base, start, end

def get_configured_port_range() -> Tuple[int, int]:
    import os
    start = int(os.getenv("VYOS_PORT_START", 32000))
    end = int(os.getenv("VYOS_PORT_END", 33000))
    return start, end

async def find_next_available_ip(db: AsyncSession, dhcp_pool: DHCPPool) -> str:
    """
    Find the next available IP in the given DHCP pool's range.
    """
    # Convert IP range to a list of all possible IPs
    from ipaddress import ip_network, ip_address # Import here to avoid top-level if not always needed

    # Assuming range_start and range_stop are full IP addresses
    start_ip = ip_address(dhcp_pool.range_start)
    end_ip = ip_address(dhcp_pool.range_stop)

    result = await db.execute(select(VMNetworkConfig.internal_ip).filter(VMNetworkConfig.dhcp_pool_id == dhcp_pool.id))
    used_ips_in_pool = {ip[0] for ip in result.all() if ip[0]} # Filter out None IPs

    # Also consider IPs used by VMs that might have been statically assigned within this pool's network,
    # but not explicitly linked to the pool. This is a more complex scenario.
    # For now, we only check IPs of VMs explicitly linked to this pool or statically assigned IPs
    # that fall within the pool's broader network range if the pool's network is defined.
    
    # A simpler approach for now: iterate from start_ip to end_ip
    current_ip = start_ip
    while current_ip <= end_ip:
        ip_str = str(current_ip)
        if ip_str not in used_ips_in_pool:
            # Double check this IP is not used by any VM, even if not linked to this pool
            # This check is important if static IPs can be assigned from within a DHCP range
            # without being formally part of the pool's dynamic assignment.
            existing_vm_with_ip_stmt = select(VMNetworkConfig).filter(VMNetworkConfig.internal_ip == ip_str)
            existing_vm_result = await db.execute(existing_vm_with_ip_stmt)
            if not existing_vm_result.scalars().first():
                 return ip_str
        current_ip += 1
    
    raise ResourceAllocationError(detail=f"No available IPs in DHCP pool '{dhcp_pool.name}' range {dhcp_pool.range_start}-{dhcp_pool.range_stop}")

async def find_next_available_port(db: AsyncSession, port_range: Dict[str, Any] = None) -> int:
    """
    Find the next available port in the given range. If port_range is None, use default config/env.
    port_range: {"start": 32000, "end": 33000}
    """
    if port_range:
        port_start = int(port_range.get("start", 32000))
        port_end = int(port_range.get("end", 33000))
    else:
        port_start, port_end = get_configured_port_range() # This is sync

    result = await db.execute(select(VMPortRule.external_port)) # Select only the column
    used_ports = {port[0] for port in result.all()} # result.all() gives list of tuples

    for port in range(port_start, port_end + 1):
        if port not in used_ports:
            return port
    raise ResourceAllocationError(detail=f"No available external ports in {port_start}-{port_end} range")

async def find_next_nat_rule_number(db: AsyncSession) -> int:
    result = await db.execute(select(VMPortRule.nat_rule_number)) # Select only the column
    used_rules = {rule_num[0] for rule_num in result.all()} # result.all() gives list of tuples
    base = 10000
    for rule in range(base, base + 10000):
        if rule not in used_rules:
            return rule
    raise ResourceAllocationError(detail="No available NAT rule numbers")

# Example error-handling wrapper for DB operations
async def safe_commit(db: AsyncSession):
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, username: str, password: str, roles: List[str]) -> User:
    hashed_pass = hash_password(password) # Hash the password before storing
    db_user = User(
        username=username,
        hashed_password=hashed_pass,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_user.roles = roles # Use the setter for roles
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    logger.info(f"User {username} created successfully with roles: {roles}") # Log user creation
    return db_user

async def get_all_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User))
    return result.scalars().all()

async def update_user(db: AsyncSession, user_to_update: User, username_new: Optional[str] = None, password_new: Optional[str] = None, roles_new: Optional[List[str]] = None) -> User:
    updated_fields = []
    if username_new is not None and user_to_update.username != username_new:
        user_to_update.username = username_new
        updated_fields.append("username")
    if password_new is not None:
        user_to_update.hashed_password = hash_password(password_new)
        updated_fields.append("password")
    if roles_new is not None and user_to_update.roles_list != roles_new: # Compare with list form
        user_to_update.roles = roles_new
        updated_fields.append("roles")
    
    if updated_fields:
        user_to_update.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user_to_update)
        logger.info(f"User {user_to_update.username} (ID: {user_to_update.id}) updated. Fields changed: {', '.join(updated_fields)}.") # Log user update
    else:
        logger.info(f"No update performed for user {user_to_update.username} (ID: {user_to_update.id}) as no new data provided or data is the same.")
    return user_to_update

async def delete_user(db: AsyncSession, user_to_delete: User):
    username = user_to_delete.username
    user_id = user_to_delete.id
    await db.delete(user_to_delete)
    await db.commit()
    logger.info(f"User {username} (ID: {user_id}) deleted successfully.") # Log user deletion

# API Key CRUD operations
async def create_api_key_for_user(db: AsyncSession, user_id: int, description: Optional[str] = None, expires_at: Optional[datetime] = None) -> APIKey:
    # Generate a unique API key string (e.g., using secrets module)
    import secrets
    new_key_value = secrets.token_urlsafe(32)
    db_api_key = APIKey(
        api_key=new_key_value,
        user_id=user_id,
        description=description,
        created_at=datetime.utcnow(),
        expires_at=expires_at
    )
    db.add(db_api_key)
    await db.commit()
    await db.refresh(db_api_key)
    logger.info(f"API Key created for user ID {user_id}.")
    return db_api_key

async def get_api_keys_for_user(db: AsyncSession, user_id: int) -> List[APIKey]:
    result = await db.execute(select(APIKey).filter(APIKey.user_id == user_id))
    return result.scalars().all()

async def get_api_key_by_value(db: AsyncSession, api_key_value: str) -> Optional[APIKey]:
    result = await db.execute(select(APIKey).filter(APIKey.api_key == api_key_value))
    return result.scalars().first()

async def get_api_key_by_id_and_user(db: AsyncSession, api_key_id: int, user_id: int) -> Optional[APIKey]:
    result = await db.execute(select(APIKey).filter(APIKey.id == api_key_id, APIKey.user_id == user_id))
    return result.scalars().first()

async def delete_api_key_for_user(db: AsyncSession, api_key_id: int, user_id: int) -> bool:
    api_key = await get_api_key_by_id_and_user(db, api_key_id, user_id)
    if api_key:
        await db.delete(api_key)
        await db.commit()
        logger.info(f"API Key ID {api_key_id} for user ID {user_id} deleted.")
        return True
    logger.warning(f"Attempt to delete non-existent API Key ID {api_key_id} for user ID {user_id} or key does not belong to user.")
    return False

async def update_api_key_for_user(db: AsyncSession, api_key_id: int, user_id: int, description: Optional[str] = None, expires_at: Optional[datetime] = None) -> Optional[APIKey]:
    api_key = await get_api_key_by_id_and_user(db, api_key_id, user_id)
    if not api_key:
        return None
    if description is not None:
        api_key.description = description
    if expires_at is not None:
        api_key.expires_at = expires_at
    api_key.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(api_key)
    logger.info(f"API Key ID {api_key_id} for user ID {user_id} updated.")
    return api_key

# Firewall Policy CRUD operations
async def create_firewall_policy(db: AsyncSession, policy: FirewallPolicyCreate, user_id: int) -> FirewallPolicy:
    # Check for existing policy with the same name for this user
    existing_policy = await get_firewall_policy_by_name(db, policy.name, user_id)
    if existing_policy:
        raise ResourceAllocationError(detail=f"Firewall policy named '{policy.name}' already exists for this user.")

    db_policy = FirewallPolicy(
        name=policy.name,
        description=policy.description,
        default_action=policy.default_action.value, # Ensure enum value is used
        user_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_policy)
    await db.commit()
    await db.refresh(db_policy)

    # Journal entry for firewall policy creation
    from crud_journal import create_journal_entry
    await create_journal_entry(db, ChangeJournalCreate(
        user_id=user_id,
        resource_type="firewall_policy",
        resource_id=str(db_policy.id),
        operation="create",
        before=None,
        after={
            "name": db_policy.name,
            "description": db_policy.description,
            "default_action": db_policy.default_action
        },
        comment="Firewall policy created"
    ))

    # Apply to VyOS
    vyos_commands = generate_firewall_policy_commands(
        policy_name=db_policy.name,
        default_action=db_policy.default_action,
        description=db_policy.description,
        action="set"
    )
    try:
        await vyos_api_call(vyos_commands)
        logger.info(f"Firewall Policy '{db_policy.name}' successfully applied to VyOS.")
    except VyOSAPIError as e:
        logger.error(f"Failed to apply Firewall Policy '{db_policy.name}' to VyOS: {e.detail}. Rolling back DB changes.")
        # Rollback DB entry if VyOS call fails
        await db.delete(db_policy)
        await db.commit()
        raise # Re-raise the VyOSAPIError to inform the client

    if policy.rules:
        for rule_data in policy.rules:
            try:
                await create_firewall_rule(db, rule_data, db_policy.id, db_policy.name) # Pass policy_name for VyOS
            except (ResourceAllocationError, VyOSAPIError) as e_rule:
                logger.error(f"Failed to create rule for policy '{db_policy.name}' due to: {e_rule}. Policy created, but this rule failed.")
                # Decide on rollback strategy: either policy is created without this rule, or policy creation fails entirely.
                # For now, let's assume policy is created, but problematic rules are skipped and error logged.
                # A more robust solution might involve a full transaction rollback for the policy if any rule fails.

    await db.refresh(db_policy) # Refresh to load the rules relationship if any were successfully created
    logger.info(f"Firewall Policy '{db_policy.name}' created in DB for user ID {user_id}. VyOS application attempted.")
    return db_policy

async def get_firewall_policy(db: AsyncSession, policy_id: int, user_id: int) -> Optional[FirewallPolicy]:
    result = await db.execute(
        select(FirewallPolicy).filter(FirewallPolicy.id == policy_id, FirewallPolicy.user_id == user_id)
    )
    return result.scalars().first()

async def get_firewall_policy_by_name(db: AsyncSession, name: str, user_id: int) -> Optional[FirewallPolicy]:
    result = await db.execute(
        select(FirewallPolicy).filter(FirewallPolicy.name == name, FirewallPolicy.user_id == user_id)
    )
    return result.scalars().first()

async def get_all_firewall_policies_for_user(db: AsyncSession, user_id: int) -> List[FirewallPolicy]:
    result = await db.execute(
        select(FirewallPolicy).filter(FirewallPolicy.user_id == user_id).order_by(FirewallPolicy.name)
    )
    return result.scalars().all()

async def update_firewall_policy(db: AsyncSession, policy_id: int, policy_update: FirewallPolicyUpdate, user_id: int) -> Optional[FirewallPolicy]:
    db_policy = await get_firewall_policy(db, policy_id, user_id)
    if not db_policy:
        return None

    original_name = db_policy.name
    original_default_action = db_policy.default_action
    original_description = db_policy.description

    update_data = policy_update.dict(exclude_unset=True)
    updated_fields_db = []
    vyos_commands_to_run = []

    if "name" in update_data and db_policy.name != update_data["name"]:
        # Check for name conflict before proceeding
        existing_policy_with_new_name = await get_firewall_policy_by_name(db, update_data["name"], user_id)
        if existing_policy_with_new_name and existing_policy_with_new_name.id != policy_id:
            raise ResourceAllocationError(detail=f"Another firewall policy named '{update_data['name']}' already exists.")
        # If name changes, old policy needs to be deleted from VyOS and new one created
        # This is complex as rules are tied to the name. Simpler: disallow name change or handle carefully.
        # For now, let's assume name change means recreating on VyOS. This is a simplification.
        # A more robust approach would be to rename if VyOS supports it, or update rules individually.
        # VyOS typically requires deleting the old named policy and creating a new one.
        logger.warning(f"Changing firewall policy name from '{original_name}' to '{update_data['name']}'. This may involve deleting and recreating the policy in VyOS.")
        # Add commands to delete old policy from VyOS (rules are part of the named policy)
        vyos_commands_to_run.extend(generate_firewall_policy_commands(original_name, original_default_action, original_description, action="delete"))
        db_policy.name = update_data["name"]
        updated_fields_db.append("name")
        # New policy will be set up later with all rules

    if "description" in update_data and db_policy.description != update_data["description"]:
        db_policy.description = update_data["description"]
        updated_fields_db.append("description")

    if "default_action" in update_data and db_policy.default_action != update_data["default_action"].value:
        db_policy.default_action = update_data["default_action"].value
        updated_fields_db.append("default_action")

    if updated_fields_db:
        db_policy.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_policy)
        # Journal entry for firewall policy update
        from crud_journal import create_journal_entry
        await create_journal_entry(db, ChangeJournalCreate(
            user_id=user_id,
            resource_type="firewall_policy",
            resource_id=str(db_policy.id),
            operation="update",
            before={
                "name": original_name,
                "description": original_description,
                "default_action": original_default_action
            },
            after={
                "name": db_policy.name,
                "description": db_policy.description,
                "default_action": db_policy.default_action
            },
            comment="Firewall policy updated"
        ))

        # Apply changes to VyOS
        # If name changed, the old policy was deleted. Now, create the new one with all its rules.
        # Otherwise, just update the existing policy.
        current_rules = await get_firewall_rules_for_policy(db, db_policy.id)
        
        vyos_policy_set_commands = generate_firewall_policy_commands(
            policy_name=db_policy.name, # Use potentially new name
            default_action=db_policy.default_action,
            description=db_policy.description,
            action="set"
        )
        vyos_commands_to_run.extend(vyos_policy_set_commands)

        for rule in current_rules:
            rule_data_for_vyos = rule.to_dict() # Assumes a to_dict() method on the model
            vyos_commands_to_run.extend(generate_firewall_rule_commands(
                policy_name=db_policy.name, # Use potentially new name
                rule_number=rule.rule_number,
                rule_data=rule_data_for_vyos,
                action="set"
            ))
        
        if vyos_commands_to_run:
            try:
                await vyos_api_call(vyos_commands_to_run)
                logger.info(f"Firewall Policy '{db_policy.name}' successfully updated/recreated in VyOS.")
            except VyOSAPIError as e:
                logger.error(f"Failed to update Firewall Policy '{db_policy.name}' in VyOS: {e.detail}. DB changes were made but VyOS update failed. Manual sync may be needed.")
                # Rollback is complex here as DB is already committed. This indicates a need for a two-phase commit or careful error handling.
                # For now, we log the error. The DB is updated, but VyOS might be out of sync.
                # Consider raising an error to inform the user of the partial success/failure.
                raise VyOSAPIError(detail=f"Policy '{db_policy.name}' updated in DB, but failed to apply to VyOS: {e.detail}. Manual sync may be required.", status_code=e.status_code)
    else:
        logger.info(f"No update performed for Firewall Policy '{db_policy.name}' (ID: {db_policy.id}).")
    
    return db_policy

async def delete_firewall_policy(db: AsyncSession, policy_id: int, user_id: int) -> bool:
    db_policy = await get_firewall_policy(db, policy_id, user_id)
    if db_policy:
        policy_name = db_policy.name # For logging and VyOS command
        
        # Delete from VyOS first
        vyos_commands = generate_firewall_policy_commands(policy_name, db_policy.default_action, db_policy.description, action="delete")
        try:
            await vyos_api_call(vyos_commands)
            logger.info(f"Firewall Policy '{policy_name}' successfully deleted from VyOS.")
        except VyOSAPIError as e:
            logger.error(f"Failed to delete Firewall Policy '{policy_name}' from VyOS: {e.detail}. DB deletion will proceed, but VyOS may be out of sync.")
            # Decide if DB deletion should proceed if VyOS fails. For now, it does.
            # Consider raising an error to inform the user of the partial success/failure.
            # raise VyOSAPIError(detail=f"Failed to delete policy '{policy_name}' from VyOS: {e.detail}. DB deletion not performed.", status_code=e.status_code)

        # Rules are cascade deleted by the relationship setting in DB
        await db.delete(db_policy)
        await db.commit()
        logger.info(f"Firewall Policy '{policy_name}' (ID: {policy_id}) deleted from DB for user ID {user_id}.")
        # Journal entry for firewall policy deletion
        from crud_journal import create_journal_entry
        from schemas import ChangeJournalCreate
        await create_journal_entry(db, ChangeJournalCreate(
            user_id=user_id,
            resource_type="firewall_policy",
            resource_id=str(policy_id),
            operation="delete",
            before={
                "name": policy_name,
                "description": db_policy.description,
                "default_action": db_policy.default_action
            },
            after=None,
            comment="Firewall policy deleted"
        ))
        return True
        
    logger.warning(f"Attempt to delete non-existent Firewall Policy ID {policy_id} for user ID {user_id} or policy does not belong to user.")
    return False

# Firewall Rule CRUD operations
async def create_firewall_rule(db: AsyncSession, rule: FirewallRuleCreate, policy_id: int, policy_name: str) -> FirewallRule: # Added policy_name
    # Check if rule number already exists for this policy
    existing_rule_check = await db.execute(
        select(FirewallRule).filter_by(policy_id=policy_id, rule_number=rule.rule_number)
    )
    if existing_rule_check.scalars().first():
        raise ResourceAllocationError(detail=f"Firewall rule number {rule.rule_number} already exists in policy ID {policy_id}.")

    rule_dict = rule.dict()
    # Convert enums to their values if necessary for model instantiation, though Pydantic usually handles this.
    if hasattr(rule_dict.get('action'), 'value'):
        rule_dict['action'] = rule_dict['action'].value
    if hasattr(rule_dict.get('protocol'), 'value'):
        rule_dict['protocol'] = rule_dict['protocol'].value

    db_rule = FirewallRule(
        policy_id=policy_id,
        **rule_dict
    )
    db_rule.created_at = datetime.utcnow()
    db_rule.updated_at = datetime.utcnow()

    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)

    # Apply to VyOS
    vyos_commands = generate_firewall_rule_commands(
        policy_name=policy_name,
        rule_number=db_rule.rule_number,
        rule_data=db_rule.to_dict(), # Assumes a to_dict() method on the model
        action="set"
    )
    try:
        await vyos_api_call(vyos_commands)
        logger.info(f"Firewall Rule {db_rule.rule_number} for policy '{policy_name}' successfully applied to VyOS.")
    except VyOSAPIError as e:
        logger.error(f"Failed to apply Firewall Rule {db_rule.rule_number} for policy '{policy_name}' to VyOS: {e.detail}. Rolling back DB changes.")
        await db.delete(db_rule)
        await db.commit()
        raise

    logger.info(f"Firewall Rule {db_rule.rule_number} created in DB for policy ID {policy_id}. VyOS application attempted.")
    return db_rule

async def get_firewall_rule(db: AsyncSession, rule_id: int, policy_id: int) -> Optional[FirewallRule]:
    # Ensure the rule belongs to the policy (indirectly checks user ownership via policy)
    result = await db.execute(
        select(FirewallRule).filter(FirewallRule.id == rule_id, FirewallRule.policy_id == policy_id)
    )
    return result.scalars().first()

async def get_firewall_rules_for_policy(db: AsyncSession, policy_id: int) -> List[FirewallRule]:
    result = await db.execute(
        select(FirewallRule).filter(FirewallRule.policy_id == policy_id).order_by(FirewallRule.rule_number)
    )
    return result.scalars().all()

async def update_firewall_rule(db: AsyncSession, rule_id: int, rule_update: FirewallRuleUpdate, policy_id: int, policy_name: str) -> Optional[FirewallRule]: # Added policy_name
    db_rule = await get_firewall_rule(db, rule_id, policy_id)
    if not db_rule:
        return None

    update_data = rule_update.dict(exclude_unset=True)
    updated_fields_db = []

    # If rule_number is being changed, check for conflicts first
    if 'rule_number' in update_data and update_data['rule_number'] != db_rule.rule_number:
        existing_rule_check = await db.execute(
            select(FirewallRule).filter_by(policy_id=policy_id, rule_number=update_data['rule_number'])
        )
        if existing_rule_check.scalars().first():
            raise ResourceAllocationError(detail=f"Firewall rule number {update_data['rule_number']} already exists in policy ID {policy_id}.")

    for key, value in update_data.items():
        # Handle enums: get value if it's an enum instance
        if hasattr(value, 'value'):
            val_to_set = value.value
        else:
            val_to_set = value
        
        if hasattr(db_rule, key) and getattr(db_rule, key) != val_to_set:
            setattr(db_rule, key, val_to_set)
            updated_fields_db.append(key)

    if updated_fields_db:
        db_rule.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_rule)
        logger.info(f"Firewall Rule {db_rule.rule_number} (ID: {db_rule.id}) in policy '{policy_name}' updated in DB. Fields changed: {', '.join(updated_fields_db)}.")

        # Apply changes to VyOS
        vyos_commands = generate_firewall_rule_commands(
            policy_name=policy_name,
            rule_number=db_rule.rule_number,
            rule_data=db_rule.to_dict(), # Assumes a to_dict() method
            action="set"
        )
        try:
            await vyos_api_call(vyos_commands)
            logger.info(f"Firewall Rule {db_rule.rule_number} for policy '{policy_name}' successfully updated in VyOS.")
        except VyOSAPIError as e:
            logger.error(f"Failed to update Firewall Rule {db_rule.rule_number} for policy '{policy_name}' in VyOS: {e.detail}. DB changes were made but VyOS update failed. Manual sync may be needed.")
            # Similar to policy update, rollback is complex. Log and potentially raise.
            raise VyOSAPIError(detail=f"Rule {db_rule.rule_number} in policy '{policy_name}' updated in DB, but failed to apply to VyOS: {e.detail}. Manual sync may be required.", status_code=e.status_code)
    else:
        logger.info(f"No update performed for Firewall Rule {db_rule.rule_number} (ID: {db_rule.id}) in policy '{policy_name}'.")
    return db_rule

async def delete_firewall_rule(db: AsyncSession, rule_id: int, policy_id: int, policy_name: str) -> bool: # Added policy_name
    db_rule = await get_firewall_rule(db, rule_id, policy_id)
    if db_rule:
        rule_number = db_rule.rule_number # For logging and VyOS command

        # Delete from VyOS first
        vyos_commands = generate_firewall_rule_commands(policy_name, rule_number, {}, action="delete") # Empty dict for rule_data on delete
        try:
            await vyos_api_call(vyos_commands)
            logger.info(f"Firewall Rule {rule_number} for policy '{policy_name}' successfully deleted from VyOS.")
        except VyOSAPIError as e:
            logger.error(f"Failed to delete Firewall Rule {rule_number} for policy '{policy_name}' from VyOS: {e.detail}. DB deletion will proceed.")
            # Decide if DB deletion should proceed. For now, it does.
            # Consider raising an error to inform the user of the partial success/failure.

        await db.delete(db_rule)
        await db.commit()
        logger.info(f"Firewall Rule {rule_number} (ID: {rule_id}) deleted from DB for policy ID {policy_id}.")
        return True
        
    logger.warning(f"Attempt to delete non-existent Firewall Rule ID {rule_id} from policy ID {policy_id} or rule does not belong to policy.")
    return False

# CRUD operations for Static Routes
async def create_static_route(db: AsyncSession, route: StaticRouteCreate, user_id: int) -> 'StaticRoute':
    existing_route_check = await db.execute(
        select(StaticRoute).where(
            StaticRoute.destination == route.destination,
            StaticRoute.next_hop == route.next_hop,
            StaticRoute.user_id == user_id
        )
    )
    if existing_route_check.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Static route with this destination and next-hop already exists for this user.")

    vyos_commands = await generate_static_route_vyos_commands(route, "set")
    try:
        # Assuming vyos_api_call returns a dict and success is indicated by no exception
        await vyos_api_call(vyos_commands) 
        logger.info(f"Static route {route.destination} -> {route.next_hop} successfully applied to VyOS.")
    except VyOSAPIError as e:
        logger.error(f"Failed to apply static route {route.destination} -> {route.next_hop} to VyOS: {e.detail}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to apply static route to VyOS: {e.detail}")

    db_route = StaticRoute(
        **route.model_dump(), 
        user_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_route)
    await db.commit()
    await db.refresh(db_route)
    return db_route

async def get_static_route(db: AsyncSession, route_id: int, user_id: Optional[int] = None) -> 'Optional[StaticRoute]':
    query = select(StaticRoute).where(StaticRoute.id == route_id)
    if user_id is not None:
        query = query.where(StaticRoute.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().first()

async def get_static_routes_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> 'List[StaticRoute]':
    result = await db.execute(
        select(StaticRoute)
        .where(StaticRoute.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_all_static_routes(db: AsyncSession, skip: int = 0, limit: int = 100) -> 'List[StaticRoute]':
    result = await db.execute(select(StaticRoute).offset(skip).limit(limit))
    return result.scalars().all()

async def update_static_route(db: AsyncSession, route_id: int, route_update: StaticRouteUpdate, requesting_user_id: int, is_admin: bool) -> 'Optional[StaticRoute]':
    db_route = await get_static_route(db, route_id)
    if not db_route:
        return None

    if not is_admin and db_route.user_id != requesting_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to update this route")

    update_data = route_update.model_dump(exclude_unset=True)

    old_vyos_route_schema = None
    if (('destination' in update_data and update_data['destination'] != db_route.destination) or \
        ('next_hop' in update_data and update_data['next_hop'] != db_route.next_hop)):
        old_vyos_route_schema = StaticRouteCreate(
            destination=db_route.destination,
            next_hop=db_route.next_hop,
            description=db_route.description,
            distance=db_route.distance
        )

    # Create a schema representing the final state for VyOS 'set' command
    final_route_data = db_route.to_dict() # Start with existing data
    final_route_data.update(update_data) # Apply updates

    # Ensure all required fields for StaticRouteCreate are present
    vyos_payload_for_set_command = StaticRouteCreate(
        destination=final_route_data['destination'],
        next_hop=final_route_data['next_hop'],
        description=final_route_data.get('description'),
        distance=final_route_data.get('distance')
    )

    if old_vyos_route_schema:
        vyos_delete_commands = await generate_static_route_vyos_commands(old_vyos_route_schema, "delete")
        try:
            await vyos_api_call(vyos_delete_commands)
            logger.info(f"Old static route {old_vyos_route_schema.destination} -> {old_vyos_route_schema.next_hop} successfully deleted from VyOS.")
        except VyOSAPIError as e:
            logger.error(f"Failed to delete old static route from VyOS: {e.detail}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to delete old static route from VyOS: {e.detail}")

    vyos_set_commands = await generate_static_route_vyos_commands(vyos_payload_for_set_command, "set")
    try:
        await vyos_api_call(vyos_set_commands)
        logger.info(f"Updated static route {vyos_payload_for_set_command.destination} -> {vyos_payload_for_set_command.next_hop} successfully applied to VyOS.")
    except VyOSAPIError as e:
        logger.error(f"Failed to apply updated static route to VyOS: {e.detail}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to apply updated static route to VyOS: {e.detail}")

    for key, value in update_data.items():
        setattr(db_route, key, value)
    db_route.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_route)

    # After DB update, log to journal
    from crud_journal import create_journal_entry
    from schemas import ChangeJournalCreate
    await create_journal_entry(db, ChangeJournalCreate(
        user_id=db_route.user_id,
        resource_type="static_route",
        resource_id=str(db_route.id),
        operation="update",
        before={
            "destination": db_route.destination,
            "next_hop": db_route.next_hop,
            "description": db_route.description,
            "distance": db_route.distance
        },
        after=update_data,
        comment="Static route updated"
    ))
    return db_route

async def delete_static_route(db: AsyncSession, route_id: int, requesting_user_id: int, is_admin: bool) -> 'Optional[StaticRoute]':
    db_route = await get_static_route(db, route_id)
    if not db_route:
        return None

    if not is_admin and db_route.user_id != requesting_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions to delete this route")

    route_schema_for_vyos = StaticRouteCreate(
        destination=db_route.destination,
        next_hop=db_route.next_hop,
        description=db_route.description,
        distance=db_route.distance
    )
    vyos_commands = await generate_static_route_vyos_commands(route_schema_for_vyos, "delete")
    try:
        await vyos_api_call(vyos_commands)
        logger.info(f"Static route {db_route.destination} -> {db_route.next_hop} successfully deleted from VyOS.")
    except VyOSAPIError as e:
        logger.error(f"Failed to delete static route from VyOS: {e.detail}. DB entry not deleted to maintain consistency.")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to delete static route from VyOS: {e.detail}. DB entry not deleted.")

    await db.delete(db_route)
    await db.commit()
    # Journal entry for static route deletion
    from crud_journal import create_journal_entry
    from schemas import ChangeJournalCreate
    await create_journal_entry(db, ChangeJournalCreate(
        user_id=db_route.user_id,
        resource_type="static_route",
        resource_id=str(route_id),
        operation="delete",
        before={
            "destination": db_route.destination,
            "next_hop": db_route.next_hop,
            "description": db_route.description,
            "distance": db_route.distance
        },
        after=None,
        comment="Static route deleted"
    ))
    return db_route

async def delete_vm(db: AsyncSession, machine_id: str):
    from vyos_core import vyos_api_call, generate_port_forward_commands
    vm = await get_vm_by_machine_id(db, machine_id)
    if not vm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="VM not found")
    # Remove NAT rules from VyOS and DB
    for rule in vm.ports:
        # Remove NAT rule from VyOS
        try:
            commands = generate_port_forward_commands(vm.internal_ip, rule.external_port, rule.port_type, action="delete")
            await vyos_api_call(commands)
        except Exception as e:
            logger.warning(f"Failed to remove NAT rule {rule.nat_rule_number} from VyOS: {e}")
        await db.delete(rule)
    # Delete VM
    await db.delete(vm)
    await db.commit()
    logger.info(f"VM {machine_id} and all associated NAT rules deleted.")
