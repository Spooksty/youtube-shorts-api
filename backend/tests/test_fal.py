import json

import httpx
import pytest

from app.config import settings
from app.integrations.base import ApiError, TransientApiError
from app.integrations.fal_video import FalVideo

MODEL = "minimax/h3-max-turbo/text-to-video"


def fake_fal(statuses, submit_status=200):
    calls = {"submit": None, "status": 0, "auth": set(), "cdn_auth": None}
    base = f"https://queue.fal.run/{MODEL}/requests/abc"

    def handler(request: httpx.Request):
        url = str(request.url)
        if url.startswith("https://queue.fal.run"):
            calls["auth"].add(request.headers.get("authorization"))
        if request.method == "POST":
            calls["submit"] = (url, json.loads(request.content))
            if submit_status != 200:
                return httpx.Response(submit_status, json={"detail": "nope"})
            return httpx.Response(200, json={"request_id": "abc", "status_url": f"{base}/status",
                                             "response_url": base})
        if url.endswith("/status"):
            status = statuses[min(calls["status"], len(statuses) - 1)]
            calls["status"] += 1
            return httpx.Response(200, json={"status": status})
        if url == base:
            return httpx.Response(200, json={"video": {"url": "https://v3b.fal.media/files/x.mp4"}})
        if url == "https://v3b.fal.media/files/x.mp4":
            calls["cdn_auth"] = request.headers.get("authorization")
            return httpx.Response(200, content=b"mp4-bytes")
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler)), calls


@pytest.fixture(autouse=True)
def fal_settings(monkeypatch):
    monkeypatch.setattr(settings, "fal_key", "test-key")
    monkeypatch.setattr(settings, "fal_video_model", MODEL)


def test_full_queue_flow(tmp_path):
    client, calls = fake_fal(["IN_QUEUE", "IN_PROGRESS", "COMPLETED"])
    result = FalVideo(client, poll_seconds=0).find_clip("cat falling", tmp_path / "visual_1", 5.6, "cats")

    url, payload = calls["submit"]
    assert url == f"https://queue.fal.run/{MODEL}"
    assert payload["aspect_ratio"] == "9:16"
    assert payload["duration"] == 6
    assert "cat falling" in payload["prompt"]
    assert calls["auth"] == {"Key test-key"}
    assert calls["cdn_auth"] is None

    path = result.data["path"]
    assert path.name == "visual_1.mp4"
    assert path.read_bytes() == b"mp4-bytes"
    assert result.service == "fal" and result.units == 6 and not result.simulated


def test_failed_generation(tmp_path):
    client, _ = fake_fal(["IN_PROGRESS", "FAILED"])
    with pytest.raises(ApiError, match="FAILED"):
        FalVideo(client, poll_seconds=0).find_clip("x", tmp_path / "v", 5)


def test_rate_limit_is_retryable(tmp_path):
    client, _ = fake_fal(["COMPLETED"], submit_status=429)
    with pytest.raises(TransientApiError):
        FalVideo(client, poll_seconds=0).find_clip("x", tmp_path / "v", 5)


def test_bad_key_is_not_retried(tmp_path):
    client, _ = fake_fal(["COMPLETED"], submit_status=401)
    with pytest.raises(ApiError) as e:
        FalVideo(client, poll_seconds=0).find_clip("x", tmp_path / "v", 5)
    assert not isinstance(e.value, TransientApiError)
