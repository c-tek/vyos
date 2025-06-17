# How to Extend VyOS API

## Custom IP/Port Pools
- Edit or add pools via the `/v1/dhcp-pools/` and `/v1/ports/` endpoints.
- Pools are stored in the database and can be managed via the API or admin UI.

## Adding New Resource Types
- Define new SQLAlchemy models in `models.py`.
- Add CRUD logic in a new or existing `crud_*.py` file.
- Register new endpoints in `routers/` or `routers.py`.

## Adding New API Endpoints
- Create a new router in `routers/` or add to `routers.py`.
- Use FastAPI's dependency injection for DB/session management.
- Document new endpoints in `api-reference.md` and `user-guide.md`.

## Customizing Authentication
- See `auth.py` for API key and JWT logic.
- Add new roles or permissions in `models.py` and `crud_rbac.py`.

## Extending Notification/Event Logic
- Add new event types in `models.py` and `crud_notifications.py`.
- Update notification delivery logic in `utils_notify_dispatch.py`.

## UI/UX Customization
- Edit `static/index.html` for the web UI.

---
For more, see `README.md` and `description_and_roadmap.md` in this directory.
