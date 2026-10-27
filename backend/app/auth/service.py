import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db, utcnow
from app.models import Administrator


class LoginError(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def authenticate(db: Session, username: str, password: str, now: datetime | None = None) -> Administrator:
    now = now or utcnow()
    admin = db.scalar(select(Administrator).where(Administrator.username == username))
    if not admin:
        raise LoginError("Nepareizs lietotājvārds vai parole")

    if admin.locked_until and admin.locked_until > now:
        raise LoginError("Konts ir bloķēts, mēģiniet vēlāk")

    if not verify_password(password, admin.password_hash):
        admin.failed_attempts += 1
        if admin.failed_attempts >= settings.max_failed_logins:
            admin.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            admin.failed_attempts = 0
            db.commit()
            raise LoginError("Konts ir bloķēts, mēģiniet vēlāk")
        db.commit()
        raise LoginError("Nepareizs lietotājvārds vai parole")

    admin.failed_attempts = 0
    admin.locked_until = None
    admin.last_login = now
    db.commit()
    return admin


def sign(payload: dict) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def unsign(token: str) -> dict | None:
    body, _, sig = token.rpartition(".")
    expected = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
    if not body or not hmac.compare_digest(sig, expected):
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(body))
    except ValueError:
        return None


def set_session_cookie(response: Response, admin_id: int):
    token = sign({"id": admin_id, "ts": int(time.time())})
    response.set_cookie("session", token, httponly=True, samesite="lax")


def current_admin(request: Request, response: Response, db: Session = Depends(get_db)) -> Administrator:
    session = unsign(request.cookies.get("session", ""))
    if not session:
        raise HTTPException(401, "Nepieciešama autorizācija")
    if time.time() - session["ts"] > settings.session_timeout_minutes * 60:
        raise HTTPException(401, "Sesija beigusies")
    admin = db.get(Administrator, session["id"])
    if not admin:
        raise HTTPException(401, "Nepieciešama autorizācija")
    set_session_cookie(response, admin.id)
    return admin
