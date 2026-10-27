import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, JobStatus, Topic
from app.workflow.context import PipelineError

RECENT_LIMIT = 30


def recently_used_topics(db: Session, channel_id: int, exclude_job: int | None = None) -> set[int]:
    q = (select(Job.topic_id)
         .where(Job.channel_id == channel_id, Job.topic_id.is_not(None),
                Job.status.in_([JobStatus.PENDING_REVIEW, JobStatus.APPROVED, JobStatus.PUBLISHED,
                                JobStatus.RUNNING]))
         .order_by(Job.created_at.desc())
         .limit(RECENT_LIMIT))
    if exclude_job:
        q = q.where(Job.id != exclude_job)
    return set(db.scalars(q))


def select_topic(db: Session, job: Job) -> Topic:
    if job.topic_id:
        return job.topic

    used = recently_used_topics(db, job.channel_id, exclude_job=job.id)
    candidates = db.scalars(select(Topic).where(Topic.channel_id == job.channel_id, Topic.is_active)).all()
    available = [t for t in candidates if t.id not in used]
    if not available:
        raise PipelineError("Nav pieejamu tēmu")
    return random.choice(available)
