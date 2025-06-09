from fastapi import APIRouter, Depends, HTTPException, status
from schemas import MCPRequest, MCPResponse, VMProvisionRequest, VMDecommissionRequest
from crud import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from routers import provision_vm, decommission_vm # Import the actual API functions
from models import User # Assuming MCP operations might need a user context, even if mocked

router = APIRouter()

@router.post("/provision", response_model=MCPResponse)
async def mcp_provision(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to provision a VM.
    Translates MCP input to VMProvisionRequest and calls the core provisioning logic.
    """
    try:
        # Extract relevant data from MCP input
        vm_provision_data = VMProvisionRequest(**req.input)
        
        # Create a dummy admin user for internal MCP calls if needed, or use a dedicated internal mechanism
        # For simplicity, assuming MCP calls are authorized internally or by a pre-authenticated context
        # In a real-world scenario, you might have a dedicated internal API key or service account.
        # For now, we'll pass a mock user with admin roles.
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")

        # Call the core provisioning logic
        provision_response = await provision_vm(vm_provision_data, db, mock_admin_user)
        
        return MCPResponse(context={"status": "success", **req.context}, output=provision_response.model_dump())
    except HTTPException as e:
        raise e # Re-raise FastAPI HTTPExceptions
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Provisioning Error: {e}")

@router.post("/decommission", response_model=MCPResponse)
async def mcp_decommission(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to decommission a VM.
    Translates MCP input to VMDecommissionRequest and calls the core decommissioning logic.
    """
    try:
        # Extract relevant data from MCP input
        vm_decommission_data = VMDecommissionRequest(**req.input)
        
        # Mock admin user for decommissioning, as it requires admin privileges
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")

        # Call the core decommissioning logic
        decommission_response = await decommission_vm(vm_decommission_data.vm_name, db, mock_admin_user)
        
        return MCPResponse(context={"status": "success", **req.context}, output=decommission_response)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Decommissioning Error: {e}")
