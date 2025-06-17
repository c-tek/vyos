import time
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict

# Simple in-memory rate limiter (per-IP, per-endpoint)
class RateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, max_requests=5, window_seconds=60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)  # { (ip, endpoint): [timestamps] }

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host
        endpoint = request.url.path
        key = (ip, endpoint)
        now = time.time()
        # Remove old attempts
        self.attempts[key] = [t for t in self.attempts[key] if now - t < self.window_seconds]
        if len(self.attempts[key]) >= self.max_requests:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests. Please try again later.")
        self.attempts[key].append(now)
        return await call_next(request)
