import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from models import NotificationRule
from schemas import NotificationRuleCreate
from crud_notifications import create_notification_rule, get_notification_rules

@pytest.mark.asyncio
async def test_create_and_query_notification_rule(async_db_session: AsyncSession):
    rule = NotificationRuleCreate(
        user_id=1,
        event_type="create",
        resource_type="vm",
        resource_id=None,
        delivery_method="email",
        target="test@example.com",
        is_active=True
    )
    created = await create_notification_rule(async_db_session, rule)
    assert created.id is not None
    assert created.event_type == "create"
    rules = await get_notification_rules(async_db_session, user_id=1, event_type="create")
    assert any(r.id == created.id for r in rules)
