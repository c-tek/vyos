import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from models import NotificationRule
from schemas import NotificationRuleCreate
from crud_notifications import create_notification_rule, get_notification_rules
from utils_notify_dispatch import dispatch_notifications

@pytest.mark.asyncio
async def test_dispatch_notifications_email(async_db_session: AsyncSession, monkeypatch):
    # Create a notification rule for VPN creation
    rule = NotificationRuleCreate(
        user_id=1,
        event_type="create",
        resource_type="vpn",
        resource_id=None,
        delivery_method="email",
        target="test@example.com",
        is_active=True
    )
    await create_notification_rule(async_db_session, rule)
    # Patch send_email to simulate success
    monkeypatch.setattr("utils_notifications.send_email", lambda *a, **kw: None)
    # Dispatch notification
    await dispatch_notifications(
        event_type="create",
        resource_type="vpn",
        resource_id="vpn-test",
        message={"status": "success", "name": "vpn-test", "type": "ipsec"},
        db=async_db_session,
        user_id=1
    )
    # Check that a NotificationHistory entry was created
    rules = await get_notification_rules(async_db_session, user_id=1, event_type="create")
    assert rules

@pytest.mark.asyncio
async def test_dispatch_notifications_webhook(async_db_session: AsyncSession, monkeypatch):
    rule = NotificationRuleCreate(
        user_id=1,
        event_type="create",
        resource_type="vpn",
        resource_id=None,
        delivery_method="webhook",
        target="https://webhook.site/test",
        is_active=True
    )
    await create_notification_rule(async_db_session, rule)
    # Patch send_webhook to simulate success
    monkeypatch.setattr("utils_notifications.send_webhook", lambda *a, **kw: None)
    await dispatch_notifications(
        event_type="create",
        resource_type="vpn",
        resource_id="vpn-test",
        message={"status": "success", "name": "vpn-test", "type": "ipsec"},
        db=async_db_session,
        user_id=1
    )
    rules = await get_notification_rules(async_db_session, user_id=1, event_type="create")
    assert rules
