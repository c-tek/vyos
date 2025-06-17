from fastapi import APIRouter, Depends, HTTPException, status
from schemas import MCPRequest, MCPResponse, VMProvisionRequest, VMDecommissionRequest
from crud import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import routers
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
        provision_response = await routers.provision_vm(vm_provision_data, db, mock_admin_user)
        
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
        vm_decommission_data = VMDecommissionRequest(**req.input)
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")
        # Use the same logic as the API endpoint for deleting a VM
        from crud import delete_vm
        await delete_vm(db, vm_decommission_data.vm_name)
        return MCPResponse(context={"status": "success", **req.context}, output={"vm_name": vm_decommission_data.vm_name})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Decommissioning Error: {e}")

@router.post("/static-routes/create", response_model=MCPResponse)
async def mcp_create_static_route(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to create a static route.
    """
    from schemas import StaticRouteCreate
    from crud import create_static_route
    try:
        static_route_data = StaticRouteCreate(**req.input)
        # For MCP, assume admin context
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")
        result = await create_static_route(db, static_route_data, mock_admin_user.id, is_admin=True)
        return MCPResponse(context={"status": "success", **req.context}, output=result.__dict__)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Create Static Route Error: {e}")

@router.get("/static-routes/list", response_model=MCPResponse)
async def mcp_list_static_routes(db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to list all static routes.
    """
    from crud import get_all_static_routes
    try:
        routes = await get_all_static_routes(db)
        return MCPResponse(context={"status": "success"}, output={"routes": [r.__dict__ for r in routes]})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP List Static Routes Error: {e}")

@router.post("/static-routes/update", response_model=MCPResponse)
async def mcp_update_static_route(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to update a static route.
    """
    from schemas import StaticRouteUpdate
    from crud import update_static_route
    try:
        route_id = req.input.get("id")
        update_data = StaticRouteUpdate(**req.input)
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")
        result = await update_static_route(db, route_id, update_data, mock_admin_user.id, is_admin=True)
        return MCPResponse(context={"status": "success", **req.context}, output=result.__dict__)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Update Static Route Error: {e}")

@router.post("/static-routes/delete", response_model=MCPResponse)
async def mcp_delete_static_route(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to delete a static route.
    """
    from crud import delete_static_route
    try:
        route_id = req.input.get("id")
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")
        result = await delete_static_route(db, route_id, mock_admin_user.id, is_admin=True)
        return MCPResponse(context={"status": "success", **req.context}, output={"deleted": True, "route_id": route_id})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Delete Static Route Error: {e}")

@router.post("/firewall/policies/create", response_model=MCPResponse)
async def mcp_create_firewall_policy(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to create a firewall policy.
    """
    from schemas import FirewallPolicyCreate
    from crud import create_firewall_policy
    try:
        policy_data = FirewallPolicyCreate(**req.input)
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")
        result = await create_firewall_policy(db, policy_data, mock_admin_user.id, is_admin=True)
        return MCPResponse(context={"status": "success", **req.context}, output=result.__dict__)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Create Firewall Policy Error: {e}")

@router.get("/firewall/policies/list", response_model=MCPResponse)
async def mcp_list_firewall_policies(db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to list all firewall policies.
    """
    from crud import get_all_firewall_policies_for_user
    try:
        # For MCP, list all policies (admin context)
        policies = await get_all_firewall_policies_for_user(db, user_id=None)
        return MCPResponse(context={"status": "success"}, output={"policies": [p.__dict__ for p in policies]})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP List Firewall Policies Error: {e}")

@router.post("/firewall/policies/update", response_model=MCPResponse)
async def mcp_update_firewall_policy(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to update a firewall policy.
    """
    from schemas import FirewallPolicyUpdate
    from crud import update_firewall_policy
    try:
        policy_id = req.input.get("id")
        update_data = FirewallPolicyUpdate(**req.input)
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")
        result = await update_firewall_policy(db, policy_id, update_data, mock_admin_user.id, is_admin=True)
        return MCPResponse(context={"status": "success", **req.context}, output=result.__dict__)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Update Firewall Policy Error: {e}")

@router.post("/firewall/policies/delete", response_model=MCPResponse)
async def mcp_delete_firewall_policy(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to delete a firewall policy.
    """
    from crud import delete_firewall_policy
    try:
        policy_id = req.input.get("id")
        mock_admin_user = User(id=0, username="mcp_admin", hashed_password="", roles="admin")
        result = await delete_firewall_policy(db, policy_id, mock_admin_user.id, is_admin=True)
        return MCPResponse(context={"status": "success", **req.context}, output={"deleted": True, "policy_id": policy_id})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Delete Firewall Policy Error: {e}")

@router.post("/quota/create", response_model=MCPResponse)
async def mcp_create_quota(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to create a quota.
    """
    from schemas import QuotaCreate
    from crud_quota import create_quota
    try:
        quota_data = QuotaCreate(**req.input)
        result = await create_quota(db, **quota_data.dict())
        return MCPResponse(context={"status": "success", **req.context}, output=result.__dict__)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Create Quota Error: {e}")

@router.get("/quota/list", response_model=MCPResponse)
async def mcp_list_quotas(db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to list all quotas.
    """
    from crud_quota import list_quotas
    try:
        quotas = await list_quotas(db)
        return MCPResponse(context={"status": "success"}, output={"quotas": [q.__dict__ for q in quotas]})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP List Quotas Error: {e}")

@router.post("/quota/update", response_model=MCPResponse)
async def mcp_update_quota(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    """
    MCP endpoint to update a quota.
    """
    from schemas import QuotaUpdate
    from crud_quota import update_quota
    from models import Quota
    try:
        quota_id = req.input.get("id")
        quota = await db.get(Quota, quota_id)
        if not quota:
            raise HTTPException(status_code=404, detail="Quota not found")
        update_data = QuotaUpdate(**req.input)
        result = await update_quota(db, quota, **update_data.dict(exclude_unset=True))
        return MCPResponse(context={"status": "success", **req.context}, output=result.__dict__)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Update Quota Error: {e}")

@router.post("/notifications/rules/create", response_model=MCPResponse)
async def mcp_create_notification_rule(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    from schemas import NotificationRuleCreate
    from crud_notifications import create_notification_rule
    try:
        rule_data = NotificationRuleCreate(**req.input)
        result = await create_notification_rule(db, rule_data)
        return MCPResponse(context={"status": "success", **req.context}, output=result.__dict__)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Create Notification Rule Error: {e}")

@router.get("/notifications/rules/list", response_model=MCPResponse)
async def mcp_list_notification_rules(db: AsyncSession = Depends(get_db)):
    from crud_notifications import list_notification_rules
    try:
        rules = await list_notification_rules(db)
        return MCPResponse(context={"status": "success"}, output={"rules": [r.__dict__ for r in rules]})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP List Notification Rules Error: {e}")

@router.post("/notifications/rules/delete", response_model=MCPResponse)
async def mcp_delete_notification_rule(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    from crud_notifications import delete_notification_rule
    try:
        rule_id = req.input.get("id")
        result = await delete_notification_rule(db, rule_id)
        return MCPResponse(context={"status": "success", **req.context}, output={"deleted": True, "rule_id": rule_id})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Delete Notification Rule Error: {e}")

@router.get("/analytics/usage", response_model=MCPResponse)
async def mcp_analytics_usage(db: AsyncSession = Depends(get_db)):
    from routers.analytics import get_usage_summary
    try:
        result = await get_usage_summary(db=db)
        return MCPResponse(context={"status": "success"}, output=result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Analytics Usage Error: {e}")

@router.get("/analytics/activity", response_model=MCPResponse)
async def mcp_analytics_activity(db: AsyncSession = Depends(get_db)):
    from routers.analytics import get_activity_report
    try:
        result = await get_activity_report(db=db)
        return MCPResponse(context={"status": "success"}, output=result)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Analytics Activity Error: {e}")

@router.post("/integrations/create", response_model=MCPResponse)
async def mcp_create_integration(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    from schemas import IntegrationCreate
    from crud_integrations import create_integration
    try:
        integration_data = IntegrationCreate(**req.input)
        result = await create_integration(db, integration_data)
        return MCPResponse(context={"status": "success", **req.context}, output=result.__dict__)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Create Integration Error: {e}")

@router.get("/integrations/list", response_model=MCPResponse)
async def mcp_list_integrations(db: AsyncSession = Depends(get_db)):
    from crud_integrations import get_integrations
    try:
        integrations = await get_integrations(db)
        return MCPResponse(context={"status": "success"}, output={"integrations": [i.__dict__ for i in integrations]})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP List Integrations Error: {e}")

@router.post("/integrations/delete", response_model=MCPResponse)
async def mcp_delete_integration(req: MCPRequest, db: AsyncSession = Depends(get_db)):
    from crud_integrations import delete_integration
    try:
        integration_id = req.input.get("id")
        result = await delete_integration(db, integration_id)
        return MCPResponse(context={"status": "success", **req.context}, output={"deleted": True, "integration_id": integration_id})
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"MCP Delete Integration Error: {e}")
