import time
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Request
from functools import wraps

# Simple in-memory rate limiter (Задание 6.5)
class RateLimiter:
    def __init__(self):
        self.requests: defaultdict = defaultdict(list)
    
    def is_allowed(self, key: str, max_requests: int, time_window_seconds: int) -> bool:
        """Check if request is allowed based on rate limit"""
        now = time.time()
        window_start = now - time_window_seconds
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        
        # Check limit
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter()

def rate_limit(max_requests: int, time_window_seconds: int, key_prefix: str = ""):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get client IP from request
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if request:
                client_ip = request.client.host if request.client else "unknown"
                key = f"{key_prefix}:{client_ip}"
            else:
                key = key_prefix
            
            if not rate_limiter.is_allowed(key, max_requests, time_window_seconds):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later."
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator