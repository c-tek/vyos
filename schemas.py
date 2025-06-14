from pydantic import BaseModel, Field, validator  # Add validator
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

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    roles: Optional[List[str]] = ["user"]  # Updated to List[str]

    @validator('roles', pre=True, always=True)
    def ensure_roles_is_list(cls, v):
        if isinstance(v, str):
            return [role.strip() for role in v.split(',') if role.strip()]
        if v is None:
            return ["user"]
        return v

class UserUpdate(UserBase):
    password: Optional[str] = None
    roles: Optional[List[str]] = None  # Updated to List[str]

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
