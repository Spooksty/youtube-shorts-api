from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.base import ApiError, call_with_retry
from app.integrations.factory import get_platform
from app.models import Publication, VideoStat
from app.workflow.costs import local_now, register_cost
from app.workflow.notifications import notify


def fetch_daily_stats(db: Session):
    today = local_now().date()
    done = set(db.scalars(select(VideoStat.publication_id).where(VideoStat.day == today)))
    pubs = [p for p in db.scalars(select(Publication)) if p.id not in done]
    if not pubs:
        return

    platform = get_platform()
    try:
        result = call_with_retry(lambda: platform.fetch_stats([p.youtube_video_id for p in pubs]))
    except ApiError as e:
        notify(db, "warning", f"Neizdevās iegūt statistiku: {e}")
        return
    register_cost(db, None, result)
    for p in pubs:
        s = result.data.get(p.youtube_video_id)
        if s:
            db.add(VideoStat(publication_id=p.id, day=today, **s))
    db.commit()
