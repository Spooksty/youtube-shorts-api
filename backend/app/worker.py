import logging
import time

from sqlalchemy import select

from app.db import SessionLocal, utcnow
from app.models import Job, JobStatus
from app.publishing.stats import fetch_daily_stats
from app.seed import init_db
from app.workflow.costs import local_now
from app.workflow.runner import run_job, run_publish
from app.workflow.scheduler import create_scheduled_jobs, recover_interrupted, release_postponed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")

POLL_SECONDS = 2


def claim_next_job() -> int | None:
    with SessionLocal() as db:
        job = db.scalars(select(Job).where(Job.status == JobStatus.WAITING)
                         .order_by(Job.created_at).limit(1).with_for_update(skip_locked=True)).first()
        if not job:
            return None
        job.status = JobStatus.RUNNING
        db.commit()
        return job.id


def due_for_publish() -> list[int]:
    with SessionLocal() as db:
        return list(db.scalars(select(Job.id).where(
            Job.status == JobStatus.APPROVED, Job.publish_after <= utcnow())))


def main():
    init_db()
    with SessionLocal() as db:
        recover_interrupted(db)
    log.info("worker started")

    last_minute = None
    last_stats_day = None
    while True:
        try:
            job_id = claim_next_job()
            if job_id:
                log.info("running job %s", job_id)
                run_job(job_id)
                continue

            for job_id in due_for_publish():
                log.info("publishing job %s", job_id)
                run_publish(job_id)

            now = local_now()
            minute = now.strftime("%Y-%m-%d %H:%M")
            if minute != last_minute:
                last_minute = minute
                with SessionLocal() as db:
                    create_scheduled_jobs(db)
                    release_postponed(db)

            if now.date() != last_stats_day:
                last_stats_day = now.date()
                with SessionLocal() as db:
                    fetch_daily_stats(db)
        except Exception:
            log.exception("worker loop error")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
