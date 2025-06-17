# How to Extend VyOS API (2025)

This guide explains how to add new features, endpoints, models, and event logic to the VyOS API.

---

## 1. Adding a New Resource
- Define a new SQLAlchemy model in `models.py`.
- Add a Pydantic schema in `schemas.py`.
- Implement CRUD logic in a new or existing `crud_*.py` file.
- Create a new router in `routers/` or add to an existing router.
- Register the router in `main.py` with an appropriate prefix.
- Add tests in `tests/unit/` and `tests/integration/`.
- Document the new endpoints in `docs/user/api-reference.md` and `docs/user/user-guide.md`.

## 2. Adding API Endpoints
- Use FastAPI's dependency injection for DB/session management.
- Use role-based access control with `RoleChecker` or similar.
- Return Pydantic models for all responses.
- Handle exceptions and log actions using `utils.py`.

## 3. Customizing Authentication & RBAC
- See `auth.py` for API key and JWT logic.
- Add new roles or permissions in `models.py` and `crud_rbac.py`.
- Update role checks in routers as needed.

## 4. Extending Notification/Event Logic
- Add new event types in `models.py` and `crud_notifications.py`.
- Update notification delivery logic in `utils_notify_dispatch.py`.

## 5. UI/UX Customization
- Edit `static/index.html` for the web UI.

## 6. Database Migrations
- Use Alembic for schema changes:
  ```bash
  alembic revision --autogenerate -m "Describe change"
  alembic upgrade head
  ```

## 7. Testing
- Add/modify tests in `tests/`.
- Run all tests with `pytest` before submitting a PR.

---

For more, see [README.md](README.md), [description_and_roadmap.md](description_and_roadmap.md), and [CONTRIBUTING.md](CONTRIBUTING.md).
