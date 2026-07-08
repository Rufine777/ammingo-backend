from fastapi import Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt
from starlette.middleware.base import BaseHTTPMiddleware
import os
from datetime import datetime
from app.routes.auth import generate_access_token
from app.db.models import User
from app.db.db import SessionLocal, get_db

secret = os.environ.get(
    "JWT_SECRET", default="dkjfaidfjei4ou9028ruq208mxuHHDUFGHjfeu9!#@*u9fj"
)
algorithm = os.environ.get("HASH_ALGORITHM", default="HS256")
EXCLUDED_PREFIXES = ("/api/login/", "/docs", "/redoc", "/openapi.json")


async def verify_token(request, call_next):
    if request.url.path.startswith(EXCLUDED_PREFIXES):
        return await call_next(request)
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        user_id = payload["user_id"]
        exp = payload["exp"]
        query = select(User).where(User.id == user_id)
        db = SessionLocal()
        request.state.db = db
        user = db.execute(query).scalars().first()
        if not user:
            return JSONResponse(status_code=403, content={"error": "Unauthorized"})
        if datetime.fromtimestamp(exp) < datetime.now():
            token = generate_access_token(user_id)
        response = await call_next(request)
        response.set_cookie(key="access_token", value=token, httponly=True, secure=True)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
    
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    payload = jwt.decode(token, secret, algorithms=[algorithm])
    user_id = payload.get("user_id")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user
