from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin.videos import job_row, log_out
from app.auth.service import current_admin, hash_password
from app.db import get_db, utcnow
from app.integrations.factory import active_providers
from app.models import Administrator, ApiCost, Channel, Job, JobLog, JobStatus, Notification, Publication
from app.workflow.costs import (budget_limit, check_budget_warning, get_setting, local_now, month_spend,
                                quota_used_today, set_setting)

router = APIRouter(tags=["reports"], dependencies=[Depends(current_admin)])


class SettingsIn(BaseModel):
    monthly_budget_eur: float
    youtube_daily_quota: int
    scheduler_enabled: bool = False


class AdminIn(BaseModel):
    username: str
    email: str
    password: str


def notification_out(n: Notification):
    return {"id": n.id, "level": n.level, "message": n.message, "job_id": n.job_id,
            "is_read": n.is_read, "created_at": n.created_at}


def budget_info(db: Session):
    spent, limit = month_spend(db), budget_limit(db)
    return {"spent": round(spent, 4), "limit": limit, "pct": round(spent / limit * 100, 1) if limit else 100}


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    today = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    published_today = db.scalar(select(func.count(Publication.id)).where(Publication.published_at >= today))
    pending = db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.PENDING_REVIEW))
    errors = db.scalar(select(func.count(Job.id)).where(
        Job.status == JobStatus.ERROR, Job.created_at >= utcnow() - timedelta(hours=24)))
    running = db.scalar(select(func.count(Job.id)).where(Job.status.in_([JobStatus.RUNNING, JobStatus.WAITING])))
    recent = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(8))
    notes = db.scalars(select(Notification).order_by(Notification.created_at.desc()).limit(6))
    return {
        "published_today": published_today, "pending_review": pending, "errors_24h": errors,
        "in_progress": running, "budget": budget_info(db),
        "quota": {"used": quota_used_today(db), "limit": int(get_setting(db, "youtube_daily_quota"))},
        "recent_jobs": [job_row(j) for j in recent],
        "notifications": [notification_out(n) for n in notes],
        "providers": active_providers(),
    }


@router.get("/logs")
def logs(job_id: int | None = None, result: str | None = None, limit: int = 200, db: Session = Depends(get_db)):
    q = select(JobLog, Channel.name).join(Job, Job.id == JobLog.job_id).join(Channel, Channel.id == Job.channel_id)
    if job_id:
        q = q.where(JobLog.job_id == job_id)
    if result:
        q = q.where(JobLog.result == result)
    rows = db.execute(q.order_by(JobLog.id.desc()).limit(min(limit, 1000))).all()
    return [{**log_out(l), "channel": name} for l, name in rows]


@router.get("/notifications")
def notifications(db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).order_by(Notification.created_at.desc()).limit(50))
    return [notification_out(n) for n in rows]


@router.post("/notifications/read-all")
def read_all(db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()
    return {"ok": True}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return {
        "monthly_budget_eur": budget_limit(db),
        "youtube_daily_quota": int(get_setting(db, "youtube_daily_quota")),
        "youtube_upload_units": int(get_setting(db, "youtube_upload_units")),
        "scheduler_enabled": get_setting(db, "scheduler_enabled") == "true",
        "budget": budget_info(db),
        "quota_used_today": quota_used_today(db),
        "providers": active_providers(),
    }


@router.put("/settings")
def save_settings(body: SettingsIn, db: Session = Depends(get_db)):
    if body.monthly_budget_eur < 0:
        raise HTTPException(400, "Budžets nevar būt negatīvs")
    if body.youtube_daily_quota <= 0:
        raise HTTPException(400, "Kvotai jābūt lielākai par 0")
    old_limit = budget_limit(db)
    set_setting(db, "monthly_budget_eur", body.monthly_budget_eur)
    set_setting(db, "youtube_daily_quota", body.youtube_daily_quota)
    set_setting(db, "scheduler_enabled", "true" if body.scheduler_enabled else "false")
    if body.monthly_budget_eur > old_limit:
        set_setting(db, "budget_warning_month", "")
    db.flush()
    check_budget_warning(db)
    db.commit()
    return get_settings(db)


@router.get("/reports/costs")
def costs_report(days: int = 30, db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=days)
    by_service = db.execute(
        select(ApiCost.service, func.count(ApiCost.id), func.sum(ApiCost.cost_eur))
        .where(ApiCost.created_at >= since).group_by(ApiCost.service)).all()
    by_channel = db.execute(
        select(Channel.name, func.count(func.distinct(Job.id)), func.sum(ApiCost.cost_eur))
        .join(Job, Job.id == ApiCost.job_id).join(Channel, Channel.id == Job.channel_id)
        .where(ApiCost.created_at >= since).group_by(Channel.name)).all()
    return {
        "by_service": [{"service": s, "requests": n, "cost_eur": round(c or 0, 4)} for s, n, c in by_service],
        "by_channel": [{"channel": ch, "jobs": n, "cost_eur": round(c or 0, 4)} for ch, n, c in by_channel],
    }


@router.get("/admins")
def admins(db: Session = Depends(get_db)):
    rows = db.scalars(select(Administrator).order_by(Administrator.id))
    now = utcnow()
    return [{"id": a.id, "username": a.username, "email": a.email, "last_login": a.last_login,
             "locked": bool(a.locked_until and a.locked_until > now)} for a in rows]


@router.post("/admins")
def create_admin(body: AdminIn, db: Session = Depends(get_db)):
    if not body.username.strip() or "@" not in body.email or len(body.password) < 8:
        raise HTTPException(400, "Nekorekti dati (parolei jābūt vismaz 8 rakstzīmēm)")
    if db.scalar(select(Administrator.id).where(Administrator.username == body.username.strip())):
        raise HTTPException(409, "Lietotājvārds jau ir aizņemts")
    db.add(Administrator(username=body.username.strip(), email=body.email.strip(),
                         password_hash=hash_password(body.password)))
    db.commit()
    return {"ok": True}
