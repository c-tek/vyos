from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
import enum
from typing import List

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
    internal_ip = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    ports = relationship("VMPortRule", back_populates="vm")

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
    is_admin = Column(Integer, default=0) # 0 for false, 1 for true
    created_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=True)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    _roles = Column("roles", String, default="user") # Renamed to _roles
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    @hybrid_property
    def roles(self) -> List[str]:
        if self._roles:
            return [role.strip() for role in self._roles.split(',') if role.strip()]
        return []

    @roles.setter
    def roles(self, roles_list: List[str]):
        self._roles = ",".join(role.strip() for role in roles_list if role.strip())

class IPPool(Base):
    __tablename__ = "ip_pools"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    base_ip = Column(String, nullable=False) # e.g., "192.168.64."
    start_octet = Column(Integer, nullable=False)
    end_octet = Column(Integer, nullable=False)
    is_active = Column(Integer, default=1) # 0 for false, 1 for true
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class PortPool(Base):
    __tablename__ = "port_pools"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    start_port = Column(Integer, nullable=False)
    end_port = Column(Integer, nullable=False)
    is_active = Column(Integer, default=1) # 0 for false, 1 for true
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

def create_db_tables(engine):
    Base.metadata.create_all(bind=engine)
