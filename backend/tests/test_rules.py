from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.auth.service import LoginError, authenticate, hash_password, sign, unsign
from app.db import Base
from app.generation.montage import ass_time, group_words
from app.generation.script import validate_script
from app.integrations.base import ApiError, ApiResult, TransientApiError, WordTiming, call_with_retry
from app.integrations.espeak_tts import estimate_timings
from app.models import Administrator, Schedule
from app.workflow.costs import next_publish_window


def script(words=75, title="A fine title", **extra):
    return {"script": " ".join(["word"] * words), "title": title, "keywords": ["sky"], **extra}


class TestScriptValidation:
    def test_valid(self):
        assert validate_script(script(), "en") is None

    def test_too_short(self):
        assert "īsu" in validate_script(script(words=20), "en")

    def test_too_long(self):
        assert "garu" in validate_script(script(words=200), "en")

    def test_title_over_100(self):
        assert validate_script(script(title="x" * 101), "en")

    def test_banned_word(self):
        data = script()
        data["script"] += " drugs"
        assert "Aizliegts" in validate_script(data, "en")

    def test_wrong_language(self):
        data = script()
        data["script"] = " ".join(["ūdeņraža"] * 75)
        assert validate_script(data, "en") == "Skripts nav angļu valodā"
        assert validate_script(data, "lv") is None


class TestRetry:
    def test_retries_then_succeeds(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise TransientApiError("503")
            return ApiResult("ok", "x", "y")

        assert call_with_retry(fn, base_delay=0).data == "ok"
        assert len(calls) == 3

    def test_gives_up_after_three_retries(self):
        calls = []

        def fn():
            calls.append(1)
            raise TransientApiError("429")

        with pytest.raises(ApiError):
            call_with_retry(fn, base_delay=0)
        assert len(calls) == 4

    def test_permanent_error_not_retried(self):
        calls = []

        def fn():
            calls.append(1)
            raise ApiError("401")

        with pytest.raises(ApiError):
            call_with_retry(fn, base_delay=0)
        assert len(calls) == 1


class TestLogin:
    @pytest.fixture
    def db(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine, tables=[Administrator.__table__])
        with Session(engine, expire_on_commit=False) as s:
            # sqlite drops tzinfo when the row is reloaded
            admin = Administrator(username="admin", email="a@b.lv", password_hash=hash_password("secret123"))
            s.add(admin)
            s.commit()
            yield s

    def test_unknown_user(self, db):
        with pytest.raises(LoginError, match="Nepareizs"):
            authenticate(db, "nobody", "x")

    def test_success_resets_counter(self, db):
        with pytest.raises(LoginError):
            authenticate(db, "admin", "wrong")
        admin = authenticate(db, "admin", "secret123")
        assert admin.failed_attempts == 0

    def test_locked_after_five_failures(self, db):
        now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        for _ in range(4):
            with pytest.raises(LoginError, match="Nepareizs"):
                authenticate(db, "admin", "wrong", now)
        with pytest.raises(LoginError, match="bloķēts"):
            authenticate(db, "admin", "wrong", now)
        # correct password still refused while locked
        with pytest.raises(LoginError, match="bloķēts"):
            authenticate(db, "admin", "secret123", now + timedelta(minutes=10))
        assert authenticate(db, "admin", "secret123", now + timedelta(minutes=16))

    def test_session_token_tamper(self):
        token = sign({"id": 1, "ts": 0})
        assert unsign(token) == {"id": 1, "ts": 0}
        assert unsign(token[:-1] + ("0" if token[-1] != "0" else "1")) is None


def test_word_timings_cover_audio():
    timings = estimate_timings("Hello there. This is a test, ok?", 4.0)
    assert len(timings) == 7
    assert timings[0].start == 0
    assert timings[-1].end == pytest.approx(4.0, abs=0.01)


def test_subtitle_groups_break_on_punctuation():
    words = [WordTiming(w, i, i + 1) for i, w in enumerate("One two. Three four five six".split())]
    groups = [[w.word for w in g] for g in group_words(words)]
    assert groups == [["One", "two."], ["Three", "four", "five"], ["six"]]
    assert ass_time(61.5) == "0:01:01.50"


def test_next_publish_window_is_tomorrow():
    tz = ZoneInfo("Europe/Riga")
    now = datetime(2026, 3, 10, 8, 0, tzinfo=tz)
    window = next_publish_window(Schedule(publish_times=["15:00", "09:00"]), now)
    assert window == datetime(2026, 3, 11, 9, 0, tzinfo=tz)
