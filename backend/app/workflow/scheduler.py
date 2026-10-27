from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import utcnow
from app.models import Channel, Job, JobStatus
from app.workflow.costs import budget_reached, get_setting, local_now
from app.workflow.notifications import notify


class JobCreationError(Exception):
    pass


def create_job(db: Session, channel_id: int, topic_id: int | None = None, manual: bool = True) -> Job:
    channel = db.get(Channel, channel_id)
    if not channel:
        raise JobCreationError("Kanāls nav atrasts")
    if not channel.is_active:
        raise JobCreationError("Kanāls nav aktīvs")

    job = Job(channel_id=channel_id, topic_id=topic_id, manual=manual, status=JobStatus.WAITING)
    db.add(job)
    db.flush()
    return job


def recover_interrupted(db: Session):
    for job in db.scalars(select(Job).where(Job.status == JobStatus.RUNNING)):
        job.status = JobStatus.ERROR
        job.error_message = "Uzdevums pārtraukts servera restartēšanas dēļ"
        job.finished_at = utcnow()
        notify(db, "error", f"Uzdevums #{job.id} pārtraukts servera restartēšanas dēļ", job.id)
    db.commit()


def create_scheduled_jobs(db: Session):
    if get_setting(db, "scheduler_enabled") != "true":
        return
    now = local_now()
    hhmm = now.strftime("%H:%M")
    channels = db.scalars(select(Channel).where(Channel.is_active)).all()
    for channel in channels:
        sched = channel.schedule
        if not sched or hhmm not in (sched.publish_times or [])[: sched.videos_per_day]:
            continue
        recent = db.scalar(select(Job.id).where(
            Job.channel_id == channel.id, Job.manual.is_(False),
            Job.created_at >= utcnow() - timedelta(minutes=2)))
        if not recent:
            create_job(db, channel.id, manual=False)
    db.commit()


def release_postponed(db: Session):
    if budget_reached(db):
        return
    for job in db.scalars(select(Job).where(Job.status == JobStatus.POSTPONED)):
        if job.channel.is_active:
            job.status = JobStatus.WAITING
    db.commit()
