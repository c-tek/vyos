from fastapi import APIRouter, Depends
from schemas import VMProvisionRequest, VMProvisionResponse
from crud import get_api_key

router = APIRouter()

@router.post("/provision", response_model=VMProvisionResponse, dependencies=[Depends(get_api_key)])
def provision_vm(req: VMProvisionRequest):
    # Dummy implementation for now
    return VMProvisionResponse(
        status="success",
        internal_ip="192.168.64.100",
        external_ports={"ssh": 32000, "http": 32001, "https": 32002},
        nat_rule_base=10001
    )
