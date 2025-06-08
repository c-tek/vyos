from fastapi import APIRouter
from schemas import MCPRequest, MCPResponse

router = APIRouter()

@router.post("/provision", response_model=MCPResponse)
def mcp_provision(req: MCPRequest):
    # Example: echo back context and input as output
    # In production, translate MCP context/input to internal logic
    return MCPResponse(context={"status": "success", **req.context}, output=req.input)

@router.post("/decommission", response_model=MCPResponse)
def mcp_decommission(req: MCPRequest):
    return MCPResponse(context={"status": "success", **req.context}, output=req.input)
