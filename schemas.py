from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

class PortActionRequest(BaseModel):
    action: Literal["create", "delete", "pause", "enable", "disable"]
    ports: Optional[List[str]] = None  # ["ssh", "http", "https"]

class VMProvisionRequest(BaseModel):
    vm_name: str
    mac_address: Optional[str] = None
    metadata: Optional[dict] = None
    ip_range: Optional[Dict[str, Any]] = None  # {"base": ..., "start": ..., "end": ...}
    port_range: Optional[Dict[str, Any]] = None  # {"start": ..., "end": ...} (future)

class VMProvisionResponse(BaseModel):
    status: str
    internal_ip: str
    external_ports: dict
    nat_rule_base: int

class VMStatusResponse(BaseModel):
    ssh: str
    http: str
    https: str

class AllVMStatusResponse(BaseModel):
    machine_id: str
    ssh: str
    http: str
    https: str

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
