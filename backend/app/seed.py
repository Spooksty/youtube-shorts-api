import time

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.auth.service import hash_password
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.generation.script import DEFAULT_TEMPLATE
from app.models import Administrator, Channel, PromptTemplate, Schedule, Topic
from app.publishing.oauth import link_channel
from app.workflow.costs import DEFAULTS, set_setting

CHANNELS = [
    {
        "name": "Wild Facts Daily", "niche": "Dzīvnieki un daba", "audience_age": "13-24", "language": "en",
        "voice_id": "TX3LPaxmHKxFdv7VOQHJ", "style": "energetic, curious", "linked": True,
        "schedule": (3, ["09:00", "15:00", "20:00"], False),
        "topics": [
            "Octopuses have three hearts", "Why flamingos are pink", "Sharks are older than trees",
            "How crows remember human faces", "Why cats always land on their feet",
            "The jellyfish that never dies", "How bees talk to each other by dancing",
            "Why owls can turn their heads so far",
        ],
    },
    {
        "name": "Space in 30s", "niche": "Kosmoss", "audience_age": "16-34", "language": "en",
        "voice_id": "pNInz6obpgDQGcFmaJgB", "style": "calm, documentary", "linked": True,
        "schedule": (2, ["12:00", "19:00"], True),
        "topics": [
            "A day on Venus is longer than its year", "There might be a planet made of diamonds",
            "The Moon is slowly drifting away from Earth", "Neutron stars are unbelievably dense",
            "Footprints on the Moon will last millions of years", "Why space is completely silent",
        ],
    },
    {
        "name": "Vēstures mīklas", "niche": "Vēsture", "audience_age": "18-45", "language": "lv",
        "voice_id": "onwK4e9ZLuTAKqWW03F9", "style": "noslēpumains, stāstošs", "linked": False,
        "schedule": (1, ["18:00"], False),
        "topics": [
            "Tunguskas sprādziens joprojām nav pilnībā izskaidrots",
            "Ēģiptes piramīdas ir pārsteidzoši precīzi orientētas",
            "Rīgā joprojām klīst leģendas par pagrīdes tuneļiem",
        ],
    },
]


def seed(db):
    db.add(Administrator(username=settings.admin_username, email="admin@example.com",
                         password_hash=hash_password(settings.admin_password)))
    for key, value in DEFAULTS.items():
        set_setting(db, key, value)

    for c in CHANNELS:
        per_day, times, auto = c["schedule"]
        channel = Channel(name=c["name"], niche=c["niche"], audience_age=c["audience_age"],
                          language=c["language"], voice_id=c["voice_id"], style=c["style"],
                          is_active=c["linked"])
        channel.schedule = Schedule(videos_per_day=per_day, publish_times=times, auto_publish=auto)
        channel.topics = [Topic(title=t) for t in c["topics"]]
        channel.templates = [PromptTemplate(name="Pamata veidne", body=DEFAULT_TEMPLATE)]
        db.add(channel)
        db.flush()
        if c["linked"]:
            link_channel(db, channel)
    db.commit()


def wait_for_db(attempts: int = 30):
    for i in range(attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            if i == attempts - 1:
                raise
            time.sleep(2)


def init_db():
    wait_for_db()
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(4242)"))
        Base.metadata.create_all(conn)

    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(4243)"))
        if db.scalar(select(Administrator.id).limit(1)) is None:
            seed(db)
        db.commit()
