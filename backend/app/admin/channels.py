import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.service import current_admin
from app.db import get_db
from app.integrations.base import ApiError
from app.integrations.factory import get_tts
from app.models import Channel, Job, JobStatus, PromptTemplate, Schedule, Topic
from app.publishing.oauth import link_channel

router = APIRouter(tags=["channels"], dependencies=[Depends(current_admin)])


class ChannelIn(BaseModel):
    name: str = ""
    niche: str = ""
    audience_age: str = ""
    language: str = "en"
    voice_id: str = ""
    style: str = ""


class TopicIn(BaseModel):
    title: str
    description: str = ""
    is_active: bool = True


class TemplateIn(BaseModel):
    name: str
    body: str
    is_active: bool = True


class ScheduleIn(BaseModel):
    videos_per_day: int
    publish_times: list[str]
    auto_publish: bool


def channel_out(c: Channel, db: Session):
    counts = {s: 0 for s in JobStatus.ALL}
    for status in db.scalars(select(Job.status).where(Job.channel_id == c.id)):
        counts[status] += 1
    return {
        "id": c.id, "name": c.name, "niche": c.niche, "audience_age": c.audience_age,
        "language": c.language, "voice_id": c.voice_id, "style": c.style, "is_active": c.is_active,
        "youtube_channel_id": c.youtube_channel_id, "linked": bool(c.youtube_channel_id),
        "topic_count": len(c.topics), "published": counts[JobStatus.PUBLISHED],
        "pending": counts[JobStatus.PENDING_REVIEW],
        "schedule": schedule_out(c.schedule) if c.schedule else None,
    }


def schedule_out(s: Schedule):
    return {"videos_per_day": s.videos_per_day, "publish_times": s.publish_times, "auto_publish": s.auto_publish}


def topic_out(t: Topic):
    return {"id": t.id, "title": t.title, "description": t.description, "is_active": t.is_active}


def template_out(t: PromptTemplate):
    return {"id": t.id, "name": t.name, "body": t.body, "version": t.version, "is_active": t.is_active}


def get_channel(db: Session, channel_id: int) -> Channel:
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(404, "Kanāls nav atrasts")
    return channel


def validate_channel(db: Session, body: ChannelIn, channel_id: int | None = None):
    required = [body.name, body.niche, body.audience_age, body.language, body.voice_id]
    if any(not v.strip() for v in required):
        raise HTTPException(400, "Jāaizpilda obligātie lauki")
    q = select(Channel.id).where(Channel.name == body.name.strip())
    if channel_id:
        q = q.where(Channel.id != channel_id)
    if db.scalar(q):
        raise HTTPException(409, "Kanāls ar šādu nosaukumu jau eksistē")


@router.get("/voices")
def list_voices():
    try:
        return get_tts().list_voices()
    except ApiError:
        return []


@router.get("/channels")
def list_channels(db: Session = Depends(get_db)):
    return [channel_out(c, db) for c in db.scalars(select(Channel).order_by(Channel.id))]


@router.get("/channels/{channel_id}")
def channel_detail(channel_id: int, db: Session = Depends(get_db)):
    return channel_out(get_channel(db, channel_id), db)


@router.post("/channels")
def create_channel(body: ChannelIn, db: Session = Depends(get_db)):
    validate_channel(db, body)
    channel = Channel(**{k: v.strip() for k, v in body.model_dump().items()}, is_active=False)
    channel.schedule = Schedule(videos_per_day=1, publish_times=["18:00"], auto_publish=False)
    db.add(channel)
    db.commit()
    return {**channel_out(channel, db), "message": "Lai aktivizētu kanālu, sasaistiet to ar YouTube"}


@router.put("/channels/{channel_id}")
def update_channel(channel_id: int, body: ChannelIn, db: Session = Depends(get_db)):
    channel = get_channel(db, channel_id)
    validate_channel(db, body, channel_id)
    for k, v in body.model_dump().items():
        setattr(channel, k, v.strip())
    db.commit()
    return channel_out(channel, db)


@router.post("/channels/{channel_id}/link")
def link_youtube(channel_id: int, db: Session = Depends(get_db)):
    channel = get_channel(db, channel_id)
    link_channel(db, channel)
    db.commit()
    return channel_out(channel, db)


@router.post("/channels/{channel_id}/active")
def set_active(channel_id: int, body: dict, db: Session = Depends(get_db)):
    channel = get_channel(db, channel_id)
    active = bool(body.get("active"))
    if active and not channel.youtube_channel_id:
        raise HTTPException(400, "Lai aktivizētu kanālu, sasaistiet to ar YouTube")
    channel.is_active = active
    db.commit()
    return channel_out(channel, db)


@router.get("/channels/{channel_id}/topics")
def list_topics(channel_id: int, db: Session = Depends(get_db)):
    get_channel(db, channel_id)
    topics = db.scalars(select(Topic).where(Topic.channel_id == channel_id).order_by(Topic.id))
    return [topic_out(t) for t in topics]


@router.post("/channels/{channel_id}/topics")
def create_topic(channel_id: int, body: TopicIn, db: Session = Depends(get_db)):
    get_channel(db, channel_id)
    if not body.title.strip():
        raise HTTPException(400, "Tēmas nosaukums ir obligāts")
    topic = Topic(channel_id=channel_id, title=body.title.strip(), description=body.description,
                  is_active=body.is_active)
    db.add(topic)
    db.commit()
    return topic_out(topic)


@router.put("/topics/{topic_id}")
def update_topic(topic_id: int, body: TopicIn, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Tēma nav atrasta")
    if not body.title.strip():
        raise HTTPException(400, "Tēmas nosaukums ir obligāts")
    topic.title, topic.description, topic.is_active = body.title.strip(), body.description, body.is_active
    db.commit()
    return topic_out(topic)


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if topic:
        db.delete(topic)
        db.commit()
    return {"ok": True}


@router.get("/channels/{channel_id}/templates")
def list_templates(channel_id: int, db: Session = Depends(get_db)):
    get_channel(db, channel_id)
    rows = db.scalars(select(PromptTemplate).where(PromptTemplate.channel_id == channel_id)
                      .order_by(PromptTemplate.id))
    return [template_out(t) for t in rows]


def check_template(body: TemplateIn):
    if not body.name.strip() or not body.body.strip():
        raise HTTPException(400, "Jāaizpilda nosaukums un veidnes teksts")
    if "{topic}" not in body.body:
        raise HTTPException(400, "Veidnē jābūt mainīgajam {topic}")
    unknown = set(re.findall(r"\{(\w+)\}", body.body)) - {"topic", "audience_age", "language", "style", "niche"}
    if unknown:
        raise HTTPException(400, f"Nezināmi mainīgie: {', '.join(sorted(unknown))}")


@router.post("/channels/{channel_id}/templates")
def create_template(channel_id: int, body: TemplateIn, db: Session = Depends(get_db)):
    get_channel(db, channel_id)
    check_template(body)
    tpl = PromptTemplate(channel_id=channel_id, name=body.name.strip(), body=body.body, is_active=body.is_active)
    db.add(tpl)
    db.commit()
    return template_out(tpl)


@router.put("/templates/{template_id}")
def update_template(template_id: int, body: TemplateIn, db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, template_id)
    if not tpl:
        raise HTTPException(404, "Veidne nav atrasta")
    check_template(body)
    if tpl.body != body.body:
        tpl.version += 1
    tpl.name, tpl.body, tpl.is_active = body.name.strip(), body.body, body.is_active
    db.commit()
    return template_out(tpl)


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    tpl = db.get(PromptTemplate, template_id)
    if tpl:
        db.delete(tpl)
        db.commit()
    return {"ok": True}


@router.put("/channels/{channel_id}/schedule")
def update_schedule(channel_id: int, body: ScheduleIn, db: Session = Depends(get_db)):
    channel = get_channel(db, channel_id)
    if not 1 <= body.videos_per_day <= 10:
        raise HTTPException(400, "Video skaitam dienā jābūt no 1 līdz 10")
    times = sorted({t.strip() for t in body.publish_times if t.strip()})
    if any(not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", t) for t in times):
        raise HTTPException(400, "Laikam jābūt formātā HH:MM")
    if len(times) < body.videos_per_day:
        raise HTTPException(400, "Publicēšanas laiku jābūt vismaz tikpat, cik video dienā")

    if not channel.schedule:
        channel.schedule = Schedule()
    channel.schedule.videos_per_day = body.videos_per_day
    channel.schedule.publish_times = times
    channel.schedule.auto_publish = body.auto_publish
    db.commit()
    return schedule_out(channel.schedule)
