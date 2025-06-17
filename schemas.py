from pydantic import BaseModel, Field, validator  # Add validator
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from models import FirewallAction, FirewallRuleProtocol, Role, Permission, UserRoleAssignment, PortProtocol, PortType # Import new enums and RBAC models

class PortActionRequest(BaseModel):
    action: Literal["create", "delete", "pause", "enable", "disable"]
    ports: Optional[List[str]] = None  # ["ssh", "http", "https"]

class VMProvisionRequest(BaseModel):
    vm_name: str
    mac_address: Optional[str] = None
    hostname: Optional[str] = None # New: hostname for the VM
    dhcp_pool_name: Optional[str] = None # New: name of the DHCP pool to use
    metadata: Optional[dict] = None
    # ip_range and port_range might be deprecated in favor of pool-based allocation
    ip_range: Optional[Dict[str, Any]] = Field(None, deprecated=True) 
    port_range: Optional[Dict[str, Any]] = Field(None, deprecated=True)

class VMProvisionResponse(BaseModel):
    status: str
    internal_ip: str
    external_ports: dict
    nat_rule_base: int
    hostname: Optional[str] = None
    dhcp_pool_name: Optional[str] = None

class VMStatusResponse(BaseModel):
    ssh: str
    http: str
    https: str

class VMPortDetail(BaseModel):
    status: str
    external_port: int | None
    nat_rule_number: int | None

class AllVMStatusResponse(BaseModel):
    machine_id: str
    internal_ip: str
    hostname: Optional[str] = None
    dhcp_pool_name: Optional[str] = None
    ports: dict[str, VMPortDetail]

class VMPortStatus(BaseModel):
    port_type: str
    status: str
    external_port: int

class MCPRequest(BaseModel):
    context: dict
    input: dict

class MCPResponse(BaseModel):
    context: dict
    output: dict

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=8) # Added min_length
    roles: Optional[List[str]] = ["user"]  # Updated to List[str]

    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 8: # Redundant check due to Field, but good for explicit error or more complex rules
            raise ValueError('Password must be at least 8 characters long.')
        # Add more complexity checks here if needed (e.g., uppercase, number, symbol)
        # For now, min_length is handled by Field, this validator is a placeholder for more rules
        # or to demonstrate how to add them.
        # If only min_length is needed, Field(..., min_length=8) is sufficient.
        # To keep it simple and rely on Field for min_length, we can simplify or remove this explicit validator
        # if no other rules are immediately needed.
        # For this iteration, let's assume Field handles it, and this is for future expansion.
        # However, for a clear error message, an explicit validator is better.
        # Let's refine to ensure it adds value beyond what Field provides.
        # For now, we'll keep the explicit check for clarity and future expansion.
        return v

    @validator('roles', pre=True, always=True)
    def ensure_roles_is_list(cls, v):
        if isinstance(v, str):
            return [role.strip() for role in v.split(',') if role.strip()]
        if v is None:
            return ["user"]
        return v

class UserUpdate(UserBase):
    password: Optional[str] = Field(None, min_length=8) # Added min_length
    roles: Optional[List[str]] = None  # Updated to List[str]

    @validator('password')
    def password_complexity_optional(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('Password must be at least 8 characters long.')
        # Add more complexity checks here if needed
        return v

    @validator('roles', pre=True, always=True)
    def ensure_roles_is_list_optional(cls, v):
        if isinstance(v, str):
            return [role.strip() for role in v.split(',') if role.strip()]
        # If None, it means no update to roles, so keep as None
        return v


class UserResponse(UserBase):
    id: int
    roles: List[str]  # Updated to List[str]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: Optional[List[str]] = None  # Updated to List[str]

class LoginRequest(BaseModel):  # Added for explicit login schema
    username: str
    password: str

# Schemas for APIKey
class APIKeyBase(BaseModel):
    description: Optional[str] = None
    expires_at: Optional[datetime] = None

class APIKeyCreate(APIKeyBase):
    pass # No additional fields needed for creation by user for themselves

class APIKeyResponse(APIKeyBase):
    id: int
    api_key: str # The key itself will be shown on creation, then perhaps only partially or not at all
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

class APIKeyUpdate(APIKeyBase):
    description: Optional[str] = None
    expires_in_days: Optional[int] = None

# Schemas for DHCPPool
class DHCPPoolBase(BaseModel):
    name: str
    subnet: str # e.g., "192.168.100.0/24"
    ip_range_start: str # e.g., "192.168.100.100"
    ip_range_end: str # e.g., "192.168.100.200"
    gateway: Optional[str] = None
    dns_servers: Optional[List[str]] = None # Changed to List[str]
    domain_name: Optional[str] = None
    lease_time: Optional[int] = 86400
    is_active: bool = True # Changed to bool, default True

    @validator('dns_servers', pre=True, always=True)
    def format_dns_servers(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(',') if s.strip()]
        return v

class DHCPPoolCreate(DHCPPoolBase):
    pass

class DHCPPoolUpdate(DHCPPoolBase):
    name: Optional[str] = None # Allow name to be optional on update, or handle separately if name changes are complex
    subnet: Optional[str] = None
    ip_range_start: Optional[str] = None
    ip_range_end: Optional[str] = None

class DHCPPoolResponse(DHCPPoolBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Schemas for FirewallRule
class FirewallRuleBase(BaseModel):
    rule_number: int = Field(..., gt=0, description="Rule number, must be unique within the policy")
    description: Optional[str] = None
    action: FirewallAction
    protocol: Optional[FirewallRuleProtocol] = None
    source_address: Optional[str] = Field(None, description="e.g., 192.168.1.0/24, 10.0.0.5, any")
    source_port: Optional[str] = Field(None, description="e.g., 80, 1000-2000, any")
    destination_address: Optional[str] = Field(None, description="e.g., 192.168.1.100, any")
    destination_port: Optional[str] = Field(None, description="e.g., 443, 3000-4000, any")
    log: bool = False
    state_established: bool = False
    state_related: bool = False
    state_new: bool = False
    state_invalid: bool = False
    is_enabled: bool = True

class FirewallRuleCreate(FirewallRuleBase):
    pass

class FirewallRuleUpdate(FirewallRuleBase):
    rule_number: Optional[int] = Field(None, gt=0)
    action: Optional[FirewallAction] = None
    # Allow all fields to be optional on update
    description: Optional[str] = None
    protocol: Optional[FirewallRuleProtocol] = None
    source_address: Optional[str] = None
    source_port: Optional[str] = None
    destination_address: Optional[str] = None
    destination_port: Optional[str] = None
    log: Optional[bool] = None
    state_established: Optional[bool] = None
    state_related: Optional[bool] = None
    state_new: Optional[bool] = None
    state_invalid: Optional[bool] = None
    is_enabled: Optional[bool] = None

class FirewallRuleResponse(FirewallRuleBase):
    id: int
    policy_id: int # Added policy_id
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Schemas for FirewallPolicy
class FirewallPolicyBase(BaseModel):
    name: str = Field(..., description="Name of the firewall policy, e.g., WAN_IN")
    description: Optional[str] = None
    default_action: FirewallAction = FirewallAction.drop

class FirewallPolicyCreate(FirewallPolicyBase):
    rules: Optional[List[FirewallRuleCreate]] = []

class FirewallPolicyUpdate(FirewallPolicyBase):
    name: Optional[str] = None # Allow name to be optional on update
    description: Optional[str] = None
    default_action: Optional[FirewallAction] = None
    # Rules are managed via their own endpoints or a dedicated sub-resource endpoint for rules under a policy

class FirewallPolicyResponse(FirewallPolicyBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    rules: List[FirewallRuleResponse] = []

    class Config:
        orm_mode = True

# Schemas for StaticRoute
class StaticRouteBase(BaseModel):
    destination: str = Field(..., description="Destination network in CIDR format, e.g., 10.0.1.0/24")
    next_hop: str = Field(..., description="Next hop IP address, e.g., 192.168.1.254")
    description: Optional[str] = None
    distance: Optional[int] = Field(1, ge=1, le=255, description="Administrative distance (1-255)")

class StaticRouteCreate(StaticRouteBase):
    pass

class StaticRouteUpdate(BaseModel):
    destination: Optional[str] = Field(None, description="Destination network in CIDR format, e.g., 10.0.1.0/24")
    next_hop: Optional[str] = Field(None, description="Next hop IP address, e.g., 192.168.1.254")
    description: Optional[str] = None
    distance: Optional[int] = Field(None, ge=1, le=255, description="Administrative distance (1-255)")

class StaticRouteResponse(StaticRouteBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class VMDecommissionRequest(BaseModel):
    vm_name: str
    reason: Optional[str] = None
    requested_by: Optional[str] = None

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[int] = None
    message: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "detail": "An error occurred.",
                "code": 400,
                "message": "Bad Request"
            }
        }

class VMNetworkConfigCreate(BaseModel):
    machine_id: str
    mac_address: str
    internal_ip: Optional[str] = None
    dhcp_pool_id: Optional[int] = None
    hostname: Optional[str] = None

class VMPortRuleCreate(BaseModel):
    vm_id: int
    port_type: str
    external_port: int
    nat_rule_number: int
    status: Optional[str] = None

# --- VPN Services ---
from pydantic import BaseModel

class VPNCreate(BaseModel):
    name: str
    type: str  # ipsec, openvpn, wireguard
    remote_address: str
    local_address: Optional[str] = None
    # --- Common fields ---
    description: Optional[str] = None
    enabled: Optional[bool] = True
    # --- IPsec-specific fields ---
    ike_version: Optional[str] = None  # e.g., 'v1', 'v2'
    encryption_algorithm: Optional[str] = None  # e.g., 'aes256', 'aes128'
    authentication_algorithm: Optional[str] = None  # e.g., 'sha256', 'sha1'
    lifetime: Optional[int] = None  # seconds
    dpd_action: Optional[str] = None  # e.g., 'restart', 'clear'
    dpd_interval: Optional[int] = None
    pre_shared_key: Optional[str] = None  # For IPsec
    # --- OpenVPN-specific fields ---
    ovpn_port: Optional[int] = None
    ovpn_protocol: Optional[str] = None  # 'udp', 'tcp'
    ovpn_cipher: Optional[str] = None
    ovpn_tls_auth: Optional[bool] = None
    ovpn_compression: Optional[bool] = None
    # --- WireGuard-specific fields ---
    public_key: Optional[str] = None
    private_key: Optional[str] = None
    allowed_ips: Optional[List[str]] = None
    listen_port: Optional[int] = None
    endpoint: Optional[str] = None
    persistent_keepalive: Optional[int] = None
    # Extend as needed for future VPN types

class VPNResponse(BaseModel):
    status: str
    name: str
    type: str
    message: Optional[str] = None

class StaticMappingRequest(BaseModel):
    mac: str
    ip: str
    description: Optional[str] = None

class StaticMappingResponse(BaseModel):
    status: str
    mac: str
    ip: str
    message: Optional[str] = None

class ConfigRestoreRequest(BaseModel):
    backup_content: str

class TaskSubmitRequest(BaseModel):
    task_type: str
    params: dict

from typing import List, Optional
from pydantic import BaseModel

class Role(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []  # List of permission strings (e.g., 'network.read', 'user.manage')

class Permission(BaseModel):
    name: str  # e.g., 'network.read'
    description: Optional[str] = None

class UserRoleAssignment(BaseModel):
    user_id: int
    role_name: str

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str]

class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]]

class QuotaBase(BaseModel):
    user_id: Optional[int] = None
    tenant_id: Optional[int] = None
    resource_type: str  # e.g., 'vm', 'network', 'firewall_rule'
    limit: int
    usage: int = 0

class QuotaCreate(QuotaBase):
    pass

class QuotaUpdate(BaseModel):
    limit: Optional[int] = None
    usage: Optional[int] = None

class QuotaResponse(QuotaBase):
    id: int

    class Config:
        orm_mode = True

class ChangeJournalEntry(BaseModel):
    id: int
    timestamp: datetime
    user_id: Optional[int] = None
    resource_type: str
    resource_id: str
    operation: str  # create, update, delete
    before: Optional[dict] = None
    after: Optional[dict] = None
    comment: Optional[str] = None

    class Config:
        orm_mode = True

class ChangeJournalCreate(BaseModel):
    user_id: Optional[int] = None
    resource_type: str
    resource_id: str
    operation: str
    before: Optional[dict] = None
    after: Optional[dict] = None
    comment: Optional[str] = None

class NotificationRuleBase(BaseModel):
    event_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    delivery_method: str  # email, webhook
    target: str  # email address or webhook URL
    is_active: bool = True

class NotificationRuleCreate(NotificationRuleBase):
    user_id: Optional[int] = None

class NotificationRuleOut(NotificationRuleBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True

class NotificationHistoryOut(BaseModel):
    id: int
    rule_id: int
    event_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    delivery_method: str
    target: str
    status: str
    message: Optional[dict] = None
    timestamp: datetime
    error: Optional[str] = None
    class Config:
        orm_mode = True

class ScheduledTaskBase(BaseModel):
    task_type: str
    payload: dict
    schedule_time: datetime
    recurrence: Optional[str] = None

class ScheduledTaskCreate(ScheduledTaskBase):
    user_id: int

class ScheduledTaskOut(ScheduledTaskBase):
    id: int
    user_id: int
    status: str
    result: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True

class SecretBase(BaseModel):
    name: str
    type: str  # generic, api_key, password, token, etc.
    is_active: bool = True

class SecretCreate(SecretBase):
    user_id: Optional[int] = None
    value: str  # plaintext, will be encrypted/hashed

class SecretOut(SecretBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None
    class Config:
        orm_mode = True

class IntegrationBase(BaseModel):
    name: str
    type: str  # webhook, plugin, etc.
    target: str
    is_active: bool = True
    config: Optional[dict] = None

class IntegrationCreate(IntegrationBase):
    user_id: Optional[int] = None

class IntegrationOut(IntegrationBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True

class HADRConfigBase(BaseModel):
    mode: str
    peer_address: Optional[str] = None
    failover_state: Optional[str] = None
    snapshot_info: Optional[dict] = None

class HADRConfigCreate(HADRConfigBase):
    pass

class HADRConfigUpdate(HADRConfigBase):
    pass

class HADRConfigResponse(HADRConfigBase):
    id: int
    last_sync_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class StaticDHCPAssignmentBase(BaseModel):
    subnet_id: int
    mac_address: str
    ip_address: str
    hostname: Optional[str] = None

class StaticDHCPAssignmentCreate(StaticDHCPAssignmentBase):
    pass

class StaticDHCPAssignmentUpdate(BaseModel):
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    hostname: Optional[str] = None

class StaticDHCPAssignmentResponse(StaticDHCPAssignmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class SubnetPortMappingBase(BaseModel):
    subnet_id: int
    external_ip: str
    external_port: int = Field(..., ge=1, le=65535)
    internal_ip: str
    internal_port: int = Field(..., ge=1, le=65535)
    protocol: PortProtocol
    description: Optional[str] = None

class SubnetPortMappingCreate(SubnetPortMappingBase):
    pass

class SubnetPortMappingUpdate(BaseModel):
    external_ip: Optional[str] = None
    external_port: Optional[int] = Field(None, ge=1, le=65535)
    internal_ip: Optional[str] = None
    internal_port: Optional[int] = Field(None, ge=1, le=65535)
    protocol: Optional[PortProtocol] = None
    description: Optional[str] = None

class SubnetPortMappingResponse(SubnetPortMappingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class SubnetBase(BaseModel):
    name: str
    cidr: str
    gateway: Optional[str] = None
    vlan_id: Optional[int] = None
    is_isolated: bool = True

class SubnetCreate(SubnetBase):
    pass

class SubnetUpdate(BaseModel):
    name: Optional[str] = None
    gateway: Optional[str] = None
    vlan_id: Optional[int] = None
    is_isolated: Optional[bool] = None

class SubnetResponse(SubnetBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class SubnetConnectionRuleBase(BaseModel):
    source_subnet_id: int
    destination_subnet_id: int
    protocol: Optional[FirewallRuleProtocol] = FirewallRuleProtocol.all
    source_port: Optional[str] = None
    destination_port: Optional[str] = None
    description: Optional[str] = None
    is_enabled: bool = True

class SubnetConnectionRuleCreate(SubnetConnectionRuleBase):
    pass

class SubnetConnectionRuleUpdate(BaseModel):
    protocol: Optional[FirewallRuleProtocol] = None
    source_port: Optional[str] = None
    destination_port: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None

class SubnetConnectionRuleResponse(SubnetConnectionRuleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Include subnet details for better API responses
    source_subnet_name: Optional[str] = None
    destination_subnet_name: Optional[str] = None

    class Config:
        orm_mode = True

class SubnetTrafficMetricsBase(BaseModel):
    subnet_id: int
    timestamp: datetime
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int
    active_hosts: int

class SubnetTrafficMetricsCreate(BaseModel):
    subnet_id: int
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int
    active_hosts: int
    # timestamp is auto-generated

class SubnetTrafficMetricsResponse(SubnetTrafficMetricsBase):
    id: int
    
    class Config:
        orm_mode = True

class SubnetTrafficSummary(BaseModel):
    subnet_id: int
    subnet_name: str
    subnet_cidr: str
    total_rx_bytes: int
    total_tx_bytes: int
    avg_rx_bytes_per_hour: float
    avg_tx_bytes_per_hour: float
    peak_rx_bytes: int
    peak_tx_bytes: int
    peak_time: Optional[datetime]
    avg_active_hosts: float
    max_active_hosts: int
    
class TimeSeriesDataPoint(BaseModel):
    timestamp: datetime
    value: float
    
class SubnetTrafficTimeSeries(BaseModel):
    subnet_id: int
    subnet_name: str
    metric: str  # "rx_bytes", "tx_bytes", "active_hosts", etc.
    interval: str  # "hourly", "daily"
    data: List[TimeSeriesDataPoint]

class BulkVMAssignmentItem(BaseModel):
    machine_id: str
    hostname: Optional[str] = None
    internal_ip: Optional[str] = None  # If not provided, will be assigned from DHCP pool

class BulkVMAssignment(BaseModel):
    subnet_id: int
    vms: List[BulkVMAssignmentItem]
    create_static_dhcp: Optional[bool] = True  # Whether to create static DHCP entries for VMs with specific IPs

class BulkVMAssignmentResponse(BaseModel):
    subnet_id: int
    subnet_name: str
    subnet_cidr: str
    successful: List[dict]  # List of successfully assigned VMs with their details
    failed: List[dict]      # List of VMs that failed to be assigned with error details
    total_requested: int
    total_successful: int
    total_failed: int

class DHCPTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    pattern: str
    start_range: Optional[int] = None
    end_range: Optional[int] = None

class DHCPTemplateCreate(DHCPTemplateBase):
    pass

class DHCPTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pattern: Optional[str] = None
    start_range: Optional[int] = None
    end_range: Optional[int] = None

class DHCPTemplateResponse(DHCPTemplateBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    class Config:
        orm_mode = True

class DHCPTemplateReservationBase(BaseModel):
    template_id: int
    subnet_id: int
    hostname_pattern: str
    start_counter: int = 1
    num_reservations: int = 0

class DHCPTemplateReservationCreate(DHCPTemplateReservationBase):
    pass

class DHCPTemplateReservationUpdate(BaseModel):
    hostname_pattern: Optional[str] = None
    start_counter: Optional[int] = None
    num_reservations: Optional[int] = None

class DHCPTemplateReservationResponse(DHCPTemplateReservationBase):
    id: int
    current_counter: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    template_name: Optional[str] = None
    subnet_name: Optional[str] = None

    class Config:
        orm_mode = True

class DHCPReservationFromTemplate(BaseModel):
    template_reservation_id: int
    count: int = 1  # How many reservations to generate
    mac_addresses: Optional[List[str]] = None  # Optional specific MAC addresses

class DHCPGeneratedReservation(BaseModel):
    id: int
    mac_address: str
    ip_address: str
    hostname: str
    subnet_id: int
