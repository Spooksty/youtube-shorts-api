from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.integrations.base import ApiResult
from app.models import ApiCost, Schedule, Setting
from app.workflow.notifications import notify

DEFAULTS = {
    "monthly_budget_eur": "20",
    "youtube_daily_quota": "100",
    "youtube_upload_units": "1",
    "budget_warning_month": "",
    "scheduler_enabled": "false",
}


def local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def get_setting(db: Session, key: str) -> str:
    row = db.get(Setting, key)
    return row.value if row else DEFAULTS[key]


def set_setting(db: Session, key: str, value):
    row = db.get(Setting, key)
    if row:
        row.value = str(value)
    else:
        db.add(Setting(key=key, value=str(value)))


def month_spend(db: Session) -> float:
    start = local_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = db.scalar(select(func.coalesce(func.sum(ApiCost.cost_eur), 0)).where(ApiCost.created_at >= start))
    return float(total)


def budget_limit(db: Session) -> float:
    return float(get_setting(db, "monthly_budget_eur"))


def budget_reached(db: Session) -> bool:
    return month_spend(db) >= budget_limit(db)


def check_budget_warning(db: Session):
    month = local_now().strftime("%Y-%m")
    if get_setting(db, "budget_warning_month") == month:
        return
    spent, limit = month_spend(db), budget_limit(db)
    if limit > 0 and spent >= limit * 0.8:
        notify(db, "warning", f"Izlietoti {spent / limit:.0%} no mēneša API budžeta ({spent:.2f} / {limit:.2f} EUR)")
        set_setting(db, "budget_warning_month", month)


def register_cost(db: Session, job_id: int | None, result: ApiResult):
    db.add(ApiCost(job_id=job_id, service=result.service, operation=result.operation,
                   units=result.units, cost_eur=result.cost_eur, simulated=result.simulated))
    db.flush()
    check_budget_warning(db)


def quota_used_today(db: Session) -> int:
    start = local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    total = db.scalar(select(func.coalesce(func.sum(ApiCost.units), 0))
                      .where(ApiCost.service == "youtube", ApiCost.operation == "videos.insert",
                             ApiCost.created_at >= start))
    return int(total)


def quota_available(db: Session) -> bool:
    limit = int(get_setting(db, "youtube_daily_quota"))
    needed = int(get_setting(db, "youtube_upload_units"))
    return quota_used_today(db) + needed <= limit


def next_publish_window(schedule: Schedule | None, now: datetime | None = None) -> datetime:
    now = now or local_now()
    times = sorted(schedule.publish_times) if schedule and schedule.publish_times else ["09:00"]
    for day_offset in range(0, 3):
        day = (now + timedelta(days=day_offset)).date()
        for t in times:
            h, m = map(int, t.split(":"))
            candidate = datetime.combine(day, time(h, m), tzinfo=now.tzinfo)
            if candidate.date() > now.date():
                return candidate
    return now + timedelta(days=1)
