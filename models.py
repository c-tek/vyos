from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, UniqueConstraint, Boolean, JSON, Text, BigInteger, Index # Added BigInteger, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
import enum
from typing import List
from datetime import datetime

Base = declarative_base()

class PortType(enum.Enum):
    ssh = "ssh"
    http = "http"
    https = "https"

class PortProtocol(enum.Enum):
    tcp = "tcp"
    udp = "udp"
    tcp_udp = "tcp_udp" # For both TCP and UDP
    all = "all" # For all protocols

class PortStatus(enum.Enum):
    enabled = "enabled"
    disabled = "disabled"
    not_active = "not_active"

class VMNetworkConfig(Base):
    __tablename__ = "vms_network_config"
    id = Column(Integer, primary_key=True)
    machine_id = Column(String, unique=True, nullable=False)
    mac_address = Column(String, unique=True, nullable=False)
    internal_ip = Column(String, unique=True, nullable=True) # Changed to nullable=True
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    ports = relationship("VMPortRule", back_populates="vm")
    hostname = Column(String, nullable=True) # New: hostname for the VM
    dhcp_pool_id = Column(Integer, ForeignKey("dhcp_pools.id"), nullable=True) # New: link to DHCPPool
    dhcp_pool = relationship("DHCPPool", back_populates="vm_network_configs") # New: relationship to DHCPPool

class VMPortRule(Base):
    __tablename__ = "vm_port_rules"
    id = Column(Integer, primary_key=True)
    vm_id = Column(Integer, ForeignKey("vms_network_config.id"))
    port_type = Column(Enum(PortType))
    external_port = Column(Integer, unique=True)
    status = Column(Enum(PortStatus), default=PortStatus.enabled)
    nat_rule_number = Column(Integer, unique=True)
    protocol = Column(Enum(PortProtocol), default=PortProtocol.tcp) # New: protocol for NAT rule
    source_ip = Column(String, nullable=True) # New: source IP for NAT rule (optional)
    custom_description = Column(String, nullable=True) # New: custom description for NAT rule (optional)
    vm = relationship("VMNetworkConfig", back_populates="ports")

class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    api_key = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # New: Foreign key to User
    user = relationship("User", back_populates="api_keys")  # New: Relationship to User

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    permissions = Column(String, nullable=False)  # Comma-separated permission strings
    assignments = relationship("UserRoleAssignment", back_populates="role", cascade="all, delete-orphan")

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", back_populates="assignments")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    _roles = Column("roles", String, default="user") # Renamed to _roles
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    firewall_policies = relationship("FirewallPolicy", back_populates="user", cascade="all, delete-orphan") # New relationship
    static_routes = relationship("StaticRoute", back_populates="user", cascade="all, delete-orphan") # New relationship
    role_assignments = relationship("UserRoleAssignment", back_populates="user", cascade="all, delete-orphan")
    change_journal_entries = relationship("ChangeJournal", back_populates="user") # New: relationship to ChangeJournal
    notification_rules = relationship("NotificationRule", back_populates="user") # New: relationship to NotificationRule
    scheduled_tasks = relationship("ScheduledTask", back_populates="user") # New: relationship to ScheduledTask
    secrets = relationship("Secret", back_populates="user") # New: relationship to Secret
    integrations = relationship("Integration", back_populates="user") # New: relationship to Integration

    @hybrid_property
    def roles(self) -> List[str]:
        if self._roles:
            return [role.strip() for role in self._roles.split(',') if role.strip()]
        return []

    @roles.setter
    def roles(self, roles_list: List[str]):
        self._roles = ",".join(role.strip() for role in roles_list if role.strip())

class SimpleIPRangePool(Base):
    __tablename__ = "simple_ip_range_pools" # Renamed table
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    base_ip = Column(String, nullable=False) # e.g., "192.168.64."
    start_octet = Column(Integer, nullable=False)
    end_octet = Column(Integer, nullable=False)
    is_active = Column(Integer, default=1) # 0 for false, 1 for true
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class SimplePortRangePool(Base):
    __tablename__ = "simple_port_range_pools" # Renamed table
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    start_port = Column(Integer, nullable=False)
    end_port = Column(Integer, nullable=False)
    is_active = Column(Integer, default=1) # 0 for false, 1 for true
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class Subnet(Base):
    __tablename__ = "subnets"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    cidr = Column(String, unique=True, nullable=False)  # e.g., "192.168.10.0/24"
    gateway = Column(String, nullable=True)
    vlan_id = Column(Integer, nullable=True)
    is_isolated = Column(Boolean, default=True)  # If true, hosts in this subnet can't see other subnets
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    dhcp_pools = relationship("DHCPPool", back_populates="subnet")

class DHCPPool(Base):
    __tablename__ = "dhcp_pools"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    subnet = Column(String, nullable=False) # e.g., "192.168.100.0/24" - Renamed from 'network' if it was different
    ip_range_start = Column(String, nullable=False) # e.g., "192.168.100.100" - Renamed from 'range_start'
    ip_range_end = Column(String, nullable=False) # e.g., "192.168.100.200" - Renamed from 'range_stop'
    gateway = Column(String, nullable=True) # e.g., "192.168.100.1" - Renamed from 'default_router'
    dns_servers = Column(String, nullable=True) # Comma-separated, e.g., "192.168.100.1,8.8.8.8"
    domain_name = Column(String, nullable=True) # e.g., "lab.local"
    lease_time = Column(Integer, default=86400) # In seconds, e.g., 86400 for 1 day
    is_active = Column(Boolean, default=True) # Changed to Boolean, default True
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    vm_network_configs = relationship("VMNetworkConfig", back_populates="dhcp_pool") # Relationship to VMNetworkConfig
    subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=True)
    subnet = relationship("Subnet", back_populates="dhcp_pools")

class FirewallAction(enum.Enum):
    accept = "accept"
    drop = "drop"
    reject = "reject"

class FirewallRuleProtocol(enum.Enum):
    tcp = "tcp"
    udp = "udp"
    icmp = "icmp"
    gre = "gre"
    esp = "esp"
    ah = "ah"
    all = "all"

class FirewallPolicy(Base):
    __tablename__ = "firewall_policies"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False) # e.g., WAN_IN, LAN_LOCAL
    description = Column(String, nullable=True)
    default_action = Column(Enum(FirewallAction), default=FirewallAction.drop)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="firewall_policies")
    rules = relationship("FirewallRule", back_populates="policy", cascade="all, delete-orphan", order_by="FirewallRule.rule_number")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "default_action": self.default_action.value if self.default_action else None,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "rules": [rule.to_dict() for rule in self.rules] # Include rules if needed
        }

class FirewallRule(Base):
    __tablename__ = "firewall_rules"
    id = Column(Integer, primary_key=True)
    policy_id = Column(Integer, ForeignKey("firewall_policies.id"), nullable=False)
    rule_number = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    action = Column(Enum(FirewallAction), nullable=False)
    protocol = Column(Enum(FirewallRuleProtocol), nullable=True) # Nullable if action doesn't need protocol (e.g. some ICMP)
    source_address = Column(String, nullable=True) # IP, CIDR, group name, or any
    source_port = Column(String, nullable=True) # Port, range, or any
    destination_address = Column(String, nullable=True) # IP, CIDR, group name, or any
    destination_port = Column(String, nullable=True) # Port, range, or any
    log = Column(Integer, default=0) # 0 for false, 1 for true (VyOS: enable/disable log)
    state_established = Column(Integer, default=0)
    state_related = Column(Integer, default=0)
    state_new = Column(Integer, default=0)
    state_invalid = Column(Integer, default=0)
    is_enabled = Column(Integer, default=1) # 0 for false (disabled), 1 for true (enabled)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    policy = relationship("FirewallPolicy", back_populates="rules")

    __table_args__ = (UniqueConstraint('policy_id', 'rule_number', name='_policy_rule_uc'),)

    def to_dict(self):
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "rule_number": self.rule_number,
            "description": self.description,
            "action": self.action.value if self.action else None,
            "protocol": self.protocol.value if self.protocol else None,
            "source_address": self.source_address,
            "source_port": self.source_port,
            "destination_address": self.destination_address,
            "destination_port": self.destination_port,
            "log": self.log == 1, # Convert to boolean
            "state_established": self.state_established == 1, # Convert to boolean
            "state_related": self.state_related == 1, # Convert to boolean
            "state_new": self.state_new == 1, # Convert to boolean
            "state_invalid": self.state_invalid == 1, # Convert to boolean
            "is_enabled": self.is_enabled == 1, # Convert to boolean
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class StaticRoute(Base):
    __tablename__ = "static_routes"
    id = Column(Integer, primary_key=True)
    destination = Column(String, nullable=False)  # e.g., "10.0.1.0/24"
    next_hop = Column(String, nullable=False)    # e.g., "192.168.1.254"
    description = Column(String, nullable=True)
    distance = Column(Integer, default=1, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="static_routes") # Add relationship to User model

    __table_args__ = (UniqueConstraint('destination', 'next_hop', 'user_id', name='_destination_nexthop_user_uc'),)

    def to_dict(self):
        return {
            "id": self.id,
            "destination": self.destination,
            "next_hop": self.next_hop,
            "description": self.description,
            "distance": self.distance,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Quota(Base):
    __tablename__ = "quotas"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tenant_id = Column(Integer, nullable=True)  # For future multi-tenant support
    resource_type = Column(String, nullable=False)
    limit = Column(Integer, nullable=False)
    usage = Column(Integer, default=0)
    user = relationship("User", backref="quotas")

class ChangeJournal(Base):
    __tablename__ = "change_journal"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    operation = Column(String, nullable=False)  # create, update, delete
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    comment = Column(Text, nullable=True)
    user = relationship("User", back_populates="change_journal_entries")

class NotificationRule(Base):
    __tablename__ = "notification_rules"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event_type = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    delivery_method = Column(String, nullable=False)  # email, webhook
    target = Column(String, nullable=False)  # email address or webhook URL
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="notification_rules")
    histories = relationship("NotificationHistory", back_populates="rule", cascade="all, delete-orphan")

class NotificationHistory(Base):
    __tablename__ = "notification_history"
    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("notification_rules.id"), nullable=False)
    event_type = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    delivery_method = Column(String, nullable=False)
    target = Column(String, nullable=False)
    status = Column(String, nullable=False)  # delivered, failed, pending
    message = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    error = Column(String, nullable=True)
    rule = relationship("NotificationRule", back_populates="histories")

class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    schedule_time = Column(DateTime, nullable=False)
    recurrence = Column(String, nullable=True)  # e.g., cron, interval
    status = Column(String, default="scheduled")  # scheduled, running, completed, failed, cancelled
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="scheduled_tasks")

class Secret(Base):
    __tablename__ = "secrets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # generic, api_key, password, token, etc.
    value = Column(String, nullable=False)  # encrypted/hashed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="secrets")
    __table_args__ = (UniqueConstraint('user_id', 'name', name='_user_secret_name_uc'),)

class Integration(Base):
    __tablename__ = "integrations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # webhook, plugin, etc.
    target = Column(String, nullable=False)  # URL or plugin identifier
    is_active = Column(Boolean, default=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="integrations")
    __table_args__ = (UniqueConstraint('user_id', 'name', name='_user_integration_name_uc'),)

class HADRMode(enum.Enum):
    standalone = "standalone"
    active = "active"
    standby = "standby"
    cluster = "cluster"

class HADRConfig(Base):
    __tablename__ = "hadr_config"
    id = Column(Integer, primary_key=True)
    mode = Column(Enum(HADRMode), default=HADRMode.standalone, nullable=False)
    peer_address = Column(String, nullable=True)  # IP or hostname of HA peer
    last_sync_time = Column(DateTime, nullable=True)
    failover_state = Column(String, nullable=True)  # e.g., "healthy", "failed_over", "degraded"
    snapshot_info = Column(JSON, nullable=True)  # Metadata about last config snapshot
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StaticDHCPAssignment(Base):
    __tablename__ = "static_dhcp_assignments"
    id = Column(Integer, primary_key=True)
    subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=False)
    mac_address = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    hostname = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subnet = relationship("Subnet")

class SubnetPortMapping(Base):
    __tablename__ = "subnet_port_mappings"
    id = Column(Integer, primary_key=True)
    subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=False)
    external_ip = Column(String, nullable=False)
    external_port = Column(Integer, nullable=False)
    internal_ip = Column(String, nullable=False)
    internal_port = Column(Integer, nullable=False)
    protocol = Column(Enum(PortProtocol), nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subnet = relationship("Subnet")
    
    __table_args__ = (
        UniqueConstraint('external_ip', 'external_port', 'protocol', name='_subnet_port_mapping_uc'),
    )

class SubnetConnectionRule(Base):
    __tablename__ = "subnet_connection_rules"
    id = Column(Integer, primary_key=True)
    source_subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=False)
    destination_subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=False)
    protocol = Column(Enum(FirewallRuleProtocol), nullable=True, default=FirewallRuleProtocol.all)
    source_port = Column(String, nullable=True)  # Can be a port number or range (e.g., "80" or "8000-8080")
    destination_port = Column(String, nullable=True)  # Can be a port number or range
    description = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    source_subnet = relationship("Subnet", foreign_keys=[source_subnet_id])
    destination_subnet = relationship("Subnet", foreign_keys=[destination_subnet_id])
    
    __table_args__ = (
        UniqueConstraint('source_subnet_id', 'destination_subnet_id', 'protocol', 'source_port', 'destination_port', name='_subnet_connection_rule_uc'),
    )

class SubnetTrafficMetrics(Base):
    __tablename__ = "subnet_traffic_metrics"
    id = Column(Integer, primary_key=True)
    subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    rx_bytes = Column(BigInteger, default=0)  # Received bytes
    tx_bytes = Column(BigInteger, default=0)  # Transmitted bytes
    rx_packets = Column(BigInteger, default=0)  # Received packets
    tx_packets = Column(BigInteger, default=0)  # Transmitted packets
    active_hosts = Column(Integer, default=0)  # Number of active hosts in the subnet
    
    subnet = relationship("Subnet")
    
    # Add index for efficient time-series queries
    __table_args__ = (
        Index('idx_subnet_metrics_subnet_time', 'subnet_id', 'timestamp'),
    )

class DHCPTemplate(Base):
    __tablename__ = "dhcp_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    pattern = Column(String, nullable=False)  # IP pattern with placeholders, e.g., "10.0.{subnet}.{host}"
    start_range = Column(Integer, nullable=True)  # Optional start range for host part
    end_range = Column(Integer, nullable=True)    # Optional end range for host part
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)    # Username who created the template

class DHCPTemplateReservation(Base):
    __tablename__ = "dhcp_template_reservations"
    id = Column(Integer, primary_key=True)
    template_id = Column(Integer, ForeignKey("dhcp_templates.id"), nullable=False)
    subnet_id = Column(Integer, ForeignKey("subnets.id"), nullable=False)
    hostname_pattern = Column(String, nullable=False)  # E.g., "web-{counter}"
    start_counter = Column(Integer, default=1)         # Start counting from this value
    current_counter = Column(Integer, default=1)       # Current counter value
    num_reservations = Column(Integer, default=0)      # How many IPs are reserved from this template
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    template = relationship("DHCPTemplate")
    subnet = relationship("Subnet")
    
    __table_args__ = (
        UniqueConstraint('template_id', 'subnet_id', name='_template_subnet_uc'),
    )

def create_db_tables(engine):
    Base.metadata.create_all(bind=engine)
