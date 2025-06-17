from fastapi import APIRouter
from . import firewall, static_routes
from .__init__ import router as feature_router

# v1 router
v1_router = APIRouter()
v1_router.include_router(firewall.router)
v1_router.include_router(static_routes.router)
v1_router.include_router(feature_router)

# For future versioning:
# v2_router = APIRouter()
# v2_router.include_router(...)
