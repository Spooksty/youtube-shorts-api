from datetime import date, datetime, time, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.service import current_admin
from app.config import settings
from app.db import get_db, utcnow
from app.models import ApiCost, Job, JobLog, JobStatus, MediaAsset, Publication, Script
from app.workflow.costs import local_now
from app.workflow.scheduler import JobCreationError, create_job

router = APIRouter(tags=["videos"], dependencies=[Depends(current_admin)])


class JobIn(BaseModel):
    channel_id: int
    topic_id: int | None = None


class MetadataIn(BaseModel):
    title: str
    description: str
    tags: list[str]


class RejectIn(BaseModel):
    regenerate: bool = False


def job_row(job: Job):
    v = job.video
    return {
        "id": job.id, "status": job.status, "channel_id": job.channel_id, "channel": job.channel.name,
        "topic": job.topic.title if job.topic else None, "title": v.title if v else None,
        "duration": v.duration if v else None, "current_step": job.current_step,
        "error": job.error_message, "manual": job.manual,
        "created_at": job.created_at, "finished_at": job.finished_at,
    }


def log_out(l: JobLog):
    return {"id": l.id, "job_id": l.job_id, "step": l.step, "result": l.result, "message": l.message,
            "started_at": l.started_at, "duration_ms": l.duration_ms}


def get_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Video nav atrasts")
    return job


@router.get("/videos")
def list_videos(channel_id: int | None = None, status: str | None = None,
                date_from: date | None = None, date_to: date | None = None,
                db: Session = Depends(get_db)):
    q = select(Job).order_by(Job.created_at.desc())
    if channel_id:
        q = q.where(Job.channel_id == channel_id)
    if status:
        q = q.where(Job.status == status)
    tz = local_now().tzinfo
    if date_from:
        q = q.where(Job.created_at >= datetime.combine(date_from, time.min, tzinfo=tz))
    if date_to:
        q = q.where(Job.created_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=tz))
    return [job_row(j) for j in db.scalars(q.limit(300))]


@router.post("/jobs")
def new_job(body: JobIn, db: Session = Depends(get_db)):
    try:
        job = create_job(db, body.channel_id, body.topic_id)
    except JobCreationError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return job_row(job)


@router.get("/videos/{job_id}")
def video_detail(job_id: int, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    v = job.video
    scripts = db.scalars(select(Script).where(Script.job_id == job_id).order_by(Script.attempt))
    media = db.scalars(select(MediaAsset).where(MediaAsset.job_id == job_id).order_by(MediaAsset.id))
    costs = db.scalars(select(ApiCost).where(ApiCost.job_id == job_id).order_by(ApiCost.id)).all()
    logs = db.scalars(select(JobLog).where(JobLog.job_id == job_id).order_by(JobLog.id))
    pub = db.scalar(select(Publication).where(Publication.video_id == v.id)) if v else None

    return {
        **job_row(job),
        "publish_after": job.publish_after,
        "video": v and {
            "title": v.title, "description": v.description, "tags": v.tags,
            "url": f"/api/media/{job.id}/final.mp4", "duration": v.duration, "width": v.width,
            "height": v.height, "has_audio": v.has_audio, "check_passed": v.check_passed,
            "script_id": v.script_id,
        },
        "scripts": [{"id": s.id, "attempt": s.attempt, "text": s.text, "title": s.title,
                     "keywords": s.keywords, "is_valid": s.is_valid,
                     "validation_message": s.validation_message} for s in scripts],
        "media": [{"id": m.id, "kind": m.kind, "provider": m.provider, "keyword": m.keyword,
                   "author": m.author, "source_url": m.source_url, "file": Path(m.path).name} for m in media],
        "costs": [{"service": c.service, "operation": c.operation, "units": c.units,
                   "cost_eur": c.cost_eur, "simulated": c.simulated} for c in costs],
        "total_cost": round(sum(c.cost_eur for c in costs), 4),
        "publication": pub and {"youtube_video_id": pub.youtube_video_id, "published_at": pub.published_at,
                                "privacy": pub.privacy, "ai_generated": pub.ai_generated},
        "logs": [log_out(l) for l in logs],
    }


def validate_metadata(body: MetadataIn):
    if not body.title.strip():
        raise HTTPException(400, "Virsraksts ir obligāts")
    if len(body.title) > 100:
        raise HTTPException(400, "Virsraksts nedrīkst pārsniegt 100 rakstzīmes")


@router.put("/videos/{job_id}/metadata")
def update_metadata(job_id: int, body: MetadataIn, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if not job.video or job.status not in (JobStatus.PENDING_REVIEW, JobStatus.APPROVED):
        raise HTTPException(400, "Šim video metadatus vairs nevar labot")
    validate_metadata(body)
    job.video.title = body.title.strip()
    job.video.description = body.description
    job.video.tags = [t.strip() for t in body.tags if t.strip()]
    db.commit()
    return video_detail(job_id, db)


@router.post("/videos/{job_id}/approve")
def approve(job_id: int, body: MetadataIn | None = None, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if job.status != JobStatus.PENDING_REVIEW:
        raise HTTPException(400, "Apstiprināt var tikai video, kas gaida apstiprinājumu")
    if body:
        validate_metadata(body)
        job.video.title, job.video.description = body.title.strip(), body.description
        job.video.tags = [t.strip() for t in body.tags if t.strip()]
    job.status = JobStatus.APPROVED
    job.video.reviewed_at = utcnow()
    # TODO: wait for the next publishing window instead
    job.publish_after = utcnow()
    db.add(JobLog(job_id=job.id, step="Pārskats", result="ok", message="Administrators apstiprināja video"))
    db.commit()
    return video_detail(job_id, db)


@router.post("/videos/{job_id}/reject")
def reject(job_id: int, body: RejectIn, db: Session = Depends(get_db)):
    job = get_job(db, job_id)
    if job.status not in (JobStatus.PENDING_REVIEW, JobStatus.ERROR):
        raise HTTPException(400, "Šo video nevar noraidīt")
    new_job = None
    if job.status == JobStatus.PENDING_REVIEW:
        job.status = JobStatus.REJECTED
        job.video.reviewed_at = utcnow()
        db.add(JobLog(job_id=job.id, step="Pārskats", result="warn", message="Administrators noraidīja video"))
    if body.regenerate:
        try:
            new_job = create_job(db, job.channel_id, job.topic_id)
        except JobCreationError as e:
            raise HTTPException(400, str(e))
    db.commit()
    return {"ok": True, "new_job_id": new_job.id if new_job else None}


@router.get("/media/{job_id}/{filename}")
def media(job_id: int, filename: str):
    path = settings.data_dir / "jobs" / str(job_id) / Path(filename).name
    if not path.is_file():
        raise HTTPException(404, "Fails nav atrasts")
    return FileResponse(path)
