from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from utils import auth

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            token = request.headers.get("Authorization").replace("Bearer ", "")
            if not token: raise AttributeError("Token not found")
        except AttributeError:
            return await call_next(request)
        # decode and verify the token here...
        user_id = auth.check_token(token)
        request.state.user_id = user_id
        return await call_next(request)
