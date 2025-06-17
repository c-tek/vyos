import logging
import os
import jwt  # Use pyjwt as jwt
from typing import Optional
from datetime import timedelta

from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Direct imports for modules in the same directory
import config  # Use config for DB session management
import models
import schemas
import auth
import mcp
import status
import admin
import crud
import vyos_core as vyos

# Imports from subdirectories using absolute path from project root
from routers import firewall as firewall_router_module
from routers import static_routes as static_routes_module
from routers import router as legacy_router
from routers import router as health_router
from routers.rbac import router as rbac_router
from routers.quota import router as quota_router

from auth import router as auth_router
from routers.static_routes import router as static_routes_router
from routers.subnets import router as subnets_router
from routers.static_dhcp import router as static_dhcp_router
from routers.port_mapping import router as port_mapping_router
from routers.subnet_connections import router as subnet_connections_router
from routers.analytics import router as analytics_router
from routers.bulk_operations import router as bulk_operations_router
from routers.dhcp_templates import router as dhcp_templates_router
from routers.topology import router as topology_router
from utils_metrics import start_metrics_tasks

ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(
    title="VyOS API Automation",
    description="API for managing VyOS instances",
    version="0.2.0",
)

# Audit logging setup
from utils import setup_audit_logger

setup_audit_logger()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# JWT Auth setup
JWT_SECRET = os.getenv("VYOS_JWT_SECRET", "changeme_jwt_secret")
JWT_ALGORITHM = "HS256"
http_bearer = HTTPBearer(auto_error=False)


async def get_user_from_token_for_logging(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Optional[str]:
    if credentials:
        try:
            payload = jwt.decode(
                credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
            )
            return payload.get("sub")
        except jwt.PyJWTError:
            return "invalid-jwt"
    return None


@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    user = request.headers.get("X-API-Key")
    if not user:
        try:
            credentials = await http_bearer(request)
            if credentials:
                token_user = await get_user_from_token_for_logging(credentials)
                if token_user:
                    user = token_user
        except Exception:
            user = "anonymous-or-error"
    if not user:
        user = "anonymous"
    response = await call_next(request)
    from utils import audit_log_action

    audit_log_action(
        user=user,
        action=f"{request.method} {request.url.path}",
        result=response.status_code,
        details={"client_ip": request.client.host if request.client else "unknown"},
    )
    return response


# Serve static files for Web UI
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")

# --- API Versioning Routers ---
from routers.versioned import v1_router

app.include_router(v1_router, prefix="/v1")
# RBAC endpoints
app.include_router(rbac_router, prefix="/v1")
app.include_router(quota_router, prefix="/v1")
app.include_router(auth_router, prefix="/v1/auth")
app.include_router(static_routes_router, prefix="/v1")
app.include_router(subnets_router, prefix="/v1")
app.include_router(static_dhcp_router, prefix="/v1")
app.include_router(port_mapping_router, prefix="/v1")
app.include_router(subnet_connections_router, prefix="/v1")
app.include_router(analytics_router, prefix="/v1")
app.include_router(bulk_operations_router, prefix="/v1")
app.include_router(dhcp_templates_router, prefix="/v1")
app.include_router(topology_router, prefix="/v1")
# For future: app.include_router(v2_router, prefix="/v2")


# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    logging.error(f"HTTPException: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url),
            }
        },
    )


from fastapi import status as fastapi_status


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "code": 500,
                "message": "An unexpected error occurred.",
                "path": str(request.url),
            }
        },
    )


# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to the VyOS API Automation service."}


@app.post("/v1/auth/token_example", tags=["Authentication"])
async def login_for_access_token_example(form_data: schemas.LoginRequest = Depends()):
    async with config.get_async_db() as db_session:  # Use config.get_async_db
        user = await auth.authenticate_user(
            db=db_session, username=form_data.username, password=form_data.password
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user.username, "roles": user.roles},
            expires_delta=access_token_expires,
        )
        return {"access_token": access_token, "token_type": "bearer"}


from utils_ratelimit import RateLimiter

app.add_middleware(RateLimiter, max_requests=5, window_seconds=60)

import asyncio
from utils_scheduled_runner import scheduled_task_runner


@app.on_event("startup")
async def start_scheduled_task_runner():
    asyncio.create_task(scheduled_task_runner())


# Start metrics collection background task
@app.on_event("startup")
async def startup_event():
    start_metrics_tasks()


if __name__ == "__main__":
    import uvicorn

    api_port = int(os.getenv("VYOS_API_PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=api_port, reload=False)
