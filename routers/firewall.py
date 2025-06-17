from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

import crud
import models
import schemas
from auth import get_api_key_auth, RoleChecker
from config import get_async_db
from exceptions import ResourceAllocationError

router = APIRouter(
    prefix="/firewall",
    tags=["Firewall Management"],
    dependencies=[Depends(get_api_key_auth)] # All firewall endpoints require API key auth
)

# --- Firewall Policy Endpoints ---

@router.post(
    "/policies",
    response_model=schemas.FirewallPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new firewall policy",
    dependencies=[Depends(RoleChecker(["admin", "netadmin"]))],
)
async def create_firewall_policy(
    policy: schemas.FirewallPolicyCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Create a new firewall policy for the authenticated user.

    - **name**: Unique name for the policy (e.g., WAN_IN, LAN_OUT).
    - **description**: Optional description.
    - **default_action**: Default action for traffic not matching any rule (drop, accept, reject).
    - **rules**: Optional list of firewall rules to create within this policy.
    """
    existing_policy = await crud.get_firewall_policy_by_name(db, name=policy.name, user_id=current_user.id)
    if existing_policy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Firewall policy with name '{policy.name}' already exists for this user."
        )
    try:
        return await crud.create_firewall_policy(db=db, policy=policy, user_id=current_user.id)
    except ResourceAllocationError as e: # Catch potential rule creation errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create firewall policy: {str(e)}")

@router.get(
    "/policies",
    response_model=List[schemas.FirewallPolicyResponse],
    summary="List all firewall policies for the current user",
)
async def list_firewall_policies(
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Retrieve all firewall policies owned by the authenticated user.
    """
    return await crud.get_all_firewall_policies_for_user(db=db, user_id=current_user.id)

@router.get(
    "/policies/{policy_id}",
    response_model=schemas.FirewallPolicyResponse,
    summary="Get a specific firewall policy",
)
async def get_firewall_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Retrieve a specific firewall policy by its ID.
    The policy must be owned by the authenticated user.
    """
    db_policy = await crud.get_firewall_policy(db=db, policy_id=policy_id, user_id=current_user.id)
    if db_policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall policy not found or not owned by user")
    return db_policy

@router.put(
    "/policies/{policy_id}",
    response_model=schemas.FirewallPolicyResponse,
    summary="Update a firewall policy",
    dependencies=[Depends(RoleChecker(["admin", "netadmin"]))],
)
async def update_firewall_policy(
    policy_id: int,
    policy_update: schemas.FirewallPolicyUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Update an existing firewall policy.

    Allows modification of name, description, and default_action.
    Rules within the policy must be managed via their specific endpoints.
    """
    if policy_update.name:
        existing_policy_with_name = await crud.get_firewall_policy_by_name(db, name=policy_update.name, user_id=current_user.id)
        if existing_policy_with_name and existing_policy_with_name.id != policy_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Another firewall policy with name '{policy_update.name}' already exists for this user."
            )
    
    updated_policy = await crud.update_firewall_policy(db=db, policy_id=policy_id, policy_update=policy_update, user_id=current_user.id)
    if updated_policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall policy not found or not owned by user")
    return updated_policy

@router.delete(
    "/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a firewall policy",
    dependencies=[Depends(RoleChecker(["admin", "netadmin"]))],
)
async def delete_firewall_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Delete a firewall policy by its ID.
    This will also delete all rules associated with this policy.
    The policy must be owned by the authenticated user.
    """
    success = await crud.delete_firewall_policy(db=db, policy_id=policy_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall policy not found or not owned by user")
    return None

# --- Firewall Rule Endpoints ---
# Rules are managed within the context of a policy

@router.post(
    "/policies/{policy_id}/rules",
    response_model=schemas.FirewallRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new rule to a firewall policy",
    dependencies=[Depends(RoleChecker(["admin", "netadmin"]))],
)
async def create_firewall_rule_for_policy(
    policy_id: int,
    rule: schemas.FirewallRuleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Add a new firewall rule to a specific policy.
    The policy must be owned by the authenticated user.

    - **rule_number**: Unique rule number within this policy.
    - **action**: accept, drop, reject.
    - **protocol**: tcp, udp, icmp, etc.
    - **source_address/port**: Source criteria.
    - **destination_address/port**: Destination criteria.
    - **log**: Enable logging for this rule.
    - **state_***: Match on connection states.
    - **is_enabled**: Whether the rule is active.
    """
    # First, verify the policy exists and belongs to the user
    policy = await crud.get_firewall_policy(db, policy_id=policy_id, user_id=current_user.id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall policy not found or not owned by user")
    
    try:
        return await crud.create_firewall_rule(db=db, rule=rule, policy_id=policy_id)
    except ResourceAllocationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create firewall rule: {str(e)}")


@router.get(
    "/policies/{policy_id}/rules",
    response_model=List[schemas.FirewallRuleResponse],
    summary="List all rules for a specific firewall policy",
)
async def list_firewall_rules_for_policy(
    policy_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Retrieve all firewall rules for a specific policy.
    The policy must be owned by the authenticated user.
    """
    policy = await crud.get_firewall_policy(db, policy_id=policy_id, user_id=current_user.id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall policy not found or not owned by user")
    return await crud.get_firewall_rules_for_policy(db=db, policy_id=policy_id)

@router.get(
    "/policies/{policy_id}/rules/{rule_id}",
    response_model=schemas.FirewallRuleResponse,
    summary="Get a specific firewall rule from a policy",
)
async def get_firewall_rule_from_policy(
    policy_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Retrieve a specific firewall rule by its ID, from a specific policy.
    The policy must be owned by the authenticated user.
    """
    policy = await crud.get_firewall_policy(db, policy_id=policy_id, user_id=current_user.id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall policy not found or not owned by user")
    
    db_rule = await crud.get_firewall_rule(db=db, rule_id=rule_id, policy_id=policy_id)
    if db_rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall rule not found in this policy")
    return db_rule

@router.put(
    "/policies/{policy_id}/rules/{rule_id}",
    response_model=schemas.FirewallRuleResponse,
    summary="Update a firewall rule in a policy",
    dependencies=[Depends(RoleChecker(["admin", "netadmin"]))],
)
async def update_firewall_rule_in_policy(
    policy_id: int,
    rule_id: int,
    rule_update: schemas.FirewallRuleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Update an existing firewall rule within a specific policy.
    The policy must be owned by the authenticated user.
    """
    policy = await crud.get_firewall_policy(db, policy_id=policy_id, user_id=current_user.id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall policy not found or not owned by user")

    try:
        updated_rule = await crud.update_firewall_rule(db=db, rule_id=rule_id, rule_update=rule_update, policy_id=policy_id)
    except ResourceAllocationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    if updated_rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall rule not found in this policy")
    return updated_rule

@router.delete(
    "/policies/{policy_id}/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a firewall rule from a policy",
    dependencies=[Depends(RoleChecker(["admin", "netadmin"]))],
)
async def delete_firewall_rule_from_policy(
    policy_id: int,
    rule_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: models.User = Depends(get_api_key_auth),
):
    """
    Delete a firewall rule by its ID, from a specific policy.
    The policy must be owned by the authenticated user.
    """
    policy = await crud.get_firewall_policy(db, policy_id=policy_id, user_id=current_user.id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall policy not found or not owned by user")

    success = await crud.delete_firewall_rule(db=db, rule_id=rule_id, policy_id=policy_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firewall rule not found in this policy")
    return None

