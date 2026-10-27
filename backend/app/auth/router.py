from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.service import LoginError, authenticate, current_admin, set_session_cookie
from app.db import get_db
from app.models import Administrator

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


def admin_out(a: Administrator):
    return {"id": a.id, "username": a.username, "email": a.email}


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    try:
        admin = authenticate(db, body.username.strip(), body.password)
    except LoginError as e:
        raise HTTPException(401, str(e))
    set_session_cookie(response, admin.id)
    return admin_out(admin)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


@router.get("/me")
def me(admin: Administrator = Depends(current_admin)):
    return admin_out(admin)
