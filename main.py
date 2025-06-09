from fastapi import FastAPI, Request, Depends, HTTPException, status
import logging
import os
from routers import router
from admin import router as admin_router
from auth import router as auth_router, oauth2_scheme, create_access_token
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt
from schemas import ErrorResponse
from models import APIKey, User
from config import engine, SessionLocal
from exceptions import APIKeyError
from crud import get_user_by_username, create_user
from datetime import timedelta
from alembic.config import Config
from alembic import command
import asyncio

app = FastAPI(title="VyOS VM Network Automation API")

# Database migrations and initial setup on startup
@app.on_event("startup")
async def on_startup():
    # Run Alembic migrations
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "migrations")
    
    # Check if the database is empty and needs initial tables
    async with engine.connect() as connection:
        inspector = await connection.run_sync(lambda sync_conn: inspect(sync_conn))
        if not await connection.run_sync(lambda sync_conn: inspector.get_table_names()):
            print("Database is empty, running initial Alembic upgrade.")
            await connection.run_sync(lambda sync_conn: command.upgrade(alembic_cfg, "head"))
        else:
            print("Database not empty, ensuring migrations are up-to-date.")
            # This will run any pending migrations
            await connection.run_sync(lambda sync_conn: command.upgrade(alembic_cfg, "head"))

    # Ensure at least one admin API key exists for initial setup
    async with SessionLocal() as db:
        if not await db.run_sync(lambda s: s.query(APIKey).filter(APIKey.is_admin == 1).first()):
            from crud import create_api_key
            import secrets
            admin_key = secrets.token_urlsafe(32)
            await db.run_sync(lambda s: create_api_key(s, admin_key, "Initial Admin Key", is_admin=True))
            print(f"\n\n!!! No admin API key found. Created a new one: {admin_key} !!!\n\n")

        # Ensure at least one admin user exists for initial JWT setup
        if not await get_user_by_username(db, "admin"):
            await create_user(db, "admin", "adminpass", roles="admin")
            print("\n\n!!! No admin user found. Created a new one: username='admin', password='adminpass' !!!\n\n")

# Audit logging setup
logging.basicConfig(
    filename="vyos_api_audit.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# Prometheus metrics setup
from prometheus_client import make_asgi_app, Counter, Histogram
from starlette.routing import Mount
from starlette.applications import Starlette

REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP Requests',
    ['method', 'endpoint', 'status_code']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP Request Latency',
    ['method', 'endpoint']
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Increment request counter
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    
    # Observe request latency
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    return response

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def _rate_limit_exceeded_handler_custom(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(detail=f"Rate limit exceeded: {exc.detail}", code="RATE_LIMIT_EXCEEDED").model_dump()
    )

# JWT Auth setup
JWT_SECRET = os.getenv("VYOS_JWT_SECRET", "changeme_jwt_secret")
JWT_ALGORITHM = "HS256"
http_bearer = HTTPBearer(auto_error=False)

async def get_jwt_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer), db: AsyncSession = Depends(SessionLocal)):
    if credentials is None:
        raise APIKeyError(detail="Missing JWT token", status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise APIKeyError(detail="Invalid JWT token (no username)", status_code=status.HTTP_401_UNAUTHORIZED)
        user = await get_user_by_username(db, username)
        if user is None:
            raise APIKeyError(detail="User not found", status_code=status.HTTP_401_UNAUTHORIZED)
        return user
    except pyjwt.PyJWTError:
        raise APIKeyError(detail="Invalid JWT token", status_code=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during JWT validation: {e}")

@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)
    user_identifier = request.headers.get("X-API-Key", None)
    if not user_identifier:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_identifier = payload.get("sub", "jwt-user")
            except Exception:
                user_identifier = "invalid-jwt"
    logging.info(f"{{'timestamp': '{datetime.utcnow().isoformat()}', 'level': 'INFO', 'message': '{request.method} {request.url.path}', 'user': '{user_identifier or 'unknown'}', 'status_code': {response.status_code}}}")
    return response

app.include_router(router, prefix="/v1")
app.include_router(admin_router, prefix="/v1/admin", tags=["Admin"])
app.include_router(auth_router, prefix="/v1", tags=["Authentication & Users"])
app.add_middleware(SlowAPIMiddleware)

@app.get("/", responses={
    status.HTTP_200_OK: {"description": "API is running"},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Rate limit exceeded"}
})
def root():
    return {"message": "VyOS VM Network Automation API is running."}

if __name__ == "__main__":
    import uvicorn
    api_port = int(os.getenv("VYOS_API_APP_PORT", 8800)) # Use VYOS_API_APP_PORT
    uvicorn.run("main:app", host="0.0.0.0", port=api_port, reload=True)
