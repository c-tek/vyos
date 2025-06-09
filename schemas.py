from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from models import PortProtocol # Import PortProtocol enum

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="A human-readable explanation of the error.")
    code: Optional[str] = Field(None, description="An optional, machine-readable error code.")
    
class ValidationErrorResponse(ErrorResponse):
    errors: List[Dict[str, Any]] = Field(..., description="Details about validation errors.")

class PortActionRequest(BaseModel):
    action: Literal["create", "delete", "pause", "enable", "disable"]
    ports: Optional[List[str]] = None  # ["ssh", "http", "https"]
    protocol: Optional[PortProtocol] = None # New: protocol for NAT rule
    source_ip: Optional[str] = None # New: source IP for NAT rule (optional)
    custom_description: Optional[str] = None # New: custom description for NAT rule (optional)

class VMProvisionRequest(BaseModel):
    vm_name: str
    mac_address: Optional[str] = None
    metadata: Optional[dict] = None
    ip_range: Optional[Dict[str, Any]] = None  # {"base": ..., "start": ..., "end": ...}
    port_range: Optional[Dict[str, Any]] = None  # {"start": ..., "end": ...} (future)
    protocol: Optional[PortProtocol] = None # New: protocol for NAT rule
    source_ip: Optional[str] = None # New: source IP for NAT rule (optional)
    custom_description: Optional[str] = None # New: custom description for NAT rule (optional)

class VMProvisionResponse(BaseModel):
    status: str
    internal_ip: str
    external_ports: dict
    nat_rule_base: int

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

class VMDecommissionRequest(BaseModel):
    vm_name: str

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str
    roles: Optional[str] = "user"

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    roles: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    roles: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class IPPoolCreate(BaseModel):
    name: str
    base_ip: str
    start_octet: int
    end_octet: int
    is_active: bool = True

class IPPoolUpdate(BaseModel):
    name: Optional[str] = None
    base_ip: Optional[str] = None
    start_octet: Optional[int] = None
    end_octet: Optional[int] = None
    is_active: Optional[bool] = None

class IPPoolResponse(BaseModel):
    id: int
    name: str
    base_ip: str
    start_octet: int
    end_octet: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PortPoolCreate(BaseModel):
    name: str
    start_port: int
    end_port: int
    is_active: bool = True

class PortPoolUpdate(BaseModel):
    name: Optional[str] = None
    start_port: Optional[int] = None
    end_port: Optional[int] = None
    is_active: Optional[bool] = None

class PortPoolResponse(BaseModel):
    id: int
    name: str
    start_port: int
    end_port: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class APIKeyCreate(BaseModel):
    description: Optional[str] = None
    is_admin: bool = False
    expires_in_days: Optional[int] = None # Number of days until expiration

class APIKeyUpdate(BaseModel):
    description: Optional[str] = None
    is_admin: Optional[bool] = None
    expires_in_days: Optional[int] = None # Number of days until expiration (0 for no expiration)

class APIKeyResponse(BaseModel):
    id: int
    api_key: str
    description: Optional[str] = None
    is_admin: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True
