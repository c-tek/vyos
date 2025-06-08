from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

class PortType(enum.Enum):
    ssh = "ssh"
    http = "http"
    https = "https"

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
    vm = relationship("VMNetworkConfig", back_populates="ports")

def create_db_tables(engine):
    Base.metadata.create_all(bind=engine)
