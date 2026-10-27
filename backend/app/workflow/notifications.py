from sqlalchemy.orm import Session

from app.models import Notification


def notify(db: Session, level: str, message: str, job_id: int | None = None):
    db.add(Notification(level=level, message=message, job_id=job_id))
