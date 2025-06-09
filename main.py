from fastapi import FastAPI, Request, Depends, HTTPException, status
import logging
import os
from routers import router
from admin import router as admin_router # Import the new admin router
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt
from schemas import LoginRequest, ErrorResponse # Import ErrorResponse
from models import create_db_tables, APIKey
from config import engine, SessionLocal
from exceptions import APIKeyError # Import custom exception

app = FastAPI(title="VyOS VM Network Automation API")

# Create database tables on startup
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(create_db_tables)
    # Ensure at least one admin API key exists for initial setup
    async with SessionLocal() as db:
        if not await db.run_sync(lambda s: s.query(APIKey).filter(APIKey.is_admin == 1).first()):
            from crud import create_api_key
            import secrets
            admin_key = secrets.token_urlsafe(32)
            await db.run_sync(lambda s: create_api_key(s, admin_key, "Initial Admin Key", is_admin=True))
            print(f"\n\n!!! No admin API key found. Created a new one: {admin_key} !!!\n\n")

# Audit logging setup
logging.basicConfig(
    filename="vyos_api_audit.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

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

def get_jwt_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)):
    if credentials is None:
        raise APIKeyError(detail="Missing JWT token", status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub", "unknown")
    except pyjwt.PyJWTError:
        raise APIKeyError(detail="Invalid JWT token", status_code=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred during JWT validation: {e}")

@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)
    user = request.headers.get("X-API-Key", None)
    if not user:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = pyjwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user = payload.get("sub", "jwt-user")
            except Exception:
                user = "invalid-jwt"
    logging.info(f"{request.method} {request.url.path} user={user or 'unknown'} status={response.status_code}")
    return response

app.include_router(router, prefix="/v1")
app.include_router(admin_router, prefix="/v1/admin", tags=["Admin"]) # Include the admin router
app.add_middleware(SlowAPIMiddleware)

@app.get("/", responses={
    status.HTTP_200_OK: {"description": "API is running"},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Rate limit exceeded"}
})
def root():
    return {"message": "VyOS VM Network Automation API is running."}

# Example: JWT login endpoint (for demo, not for production use)
# TODO: For full async support, refactor DB and VyOS calls to async-compatible libraries and update endpoints to async def.

if __name__ == "__main__":
    import uvicorn
    api_port = int(os.getenv("VYOS_API_PORT", 8800))
    uvicorn.run("main:app", host="0.0.0.0", port=api_port, reload=True)
