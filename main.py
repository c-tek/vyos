from fastapi import FastAPI, Request, Depends, HTTPException, status
import logging
import os
from routers import router
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt

app = FastAPI(title="VyOS VM Network Automation API")

# Audit logging setup
logging.basicConfig(
    filename="vyos_api_audit.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# JWT Auth setup
JWT_SECRET = os.getenv("VYOS_JWT_SECRET", "changeme_jwt_secret")
JWT_ALGORITHM = "HS256"
http_bearer = HTTPBearer(auto_error=False)

def get_jwt_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing JWT token")
    try:
        payload = pyjwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub", "unknown")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid JWT token")

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

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    response = await limiter(request, call_next)
    return response

app.include_router(router)

@app.get("/")
def root():
    return {"message": "VyOS VM Network Automation API is running."}

# Example: JWT login endpoint (for demo, not for production use)
@app.post("/auth/jwt")
def login_jwt(username: str, password: str):
    # For demo: accept any username/password, in production check securely
    if username and password:
        token = pyjwt.encode({"sub": username}, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

# TODO: For full async support, refactor DB and VyOS calls to async-compatible libraries and update endpoints to async def.

if __name__ == "__main__":
    import uvicorn
    api_port = int(os.getenv("VYOS_API_PORT", 8800))
    uvicorn.run("main:app", host="0.0.0.0", port=api_port, reload=True)
