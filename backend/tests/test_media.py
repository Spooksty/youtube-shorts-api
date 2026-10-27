import httpx
import pytest

from app.config import settings
from app.integrations import factory
from app.integrations.base import ApiError, ApiResult
from app.integrations.fal_images import FalImages
from app.integrations.pixabay_adapter import PixabayAdapter, query_variants


def hit(id, w, h, duration=10, tags="cat, octopus, coral, animal"):
    return {"id": id, "duration": duration, "tags": tags, "user": f"user{id}", "pageURL": f"https://pixabay.com/videos/{id}/",
            "videos": {"medium": {"url": f"https://cdn.pixabay.com/{id}.mp4", "width": w, "height": h,
                                  "thumbnail": f"https://cdn.pixabay.com/{id}.jpg"}}}


def pixabay(results: dict):
    searches = []

    def handler(request: httpx.Request):
        if request.url.host == "pixabay.com":
            q = request.url.params["q"]
            searches.append(q)
            assert request.url.params["key"] == "pk"
            return httpx.Response(200, json={"hits": results.get(q, [])})
        return httpx.Response(200, content=b"clip")

    return httpx.Client(transport=httpx.MockTransport(handler)), searches


@pytest.fixture(autouse=True)
def keys(monkeypatch):
    monkeypatch.setattr(settings, "pixabay_api_key", "pk")
    monkeypatch.setattr(settings, "fal_key", "fk")
    monkeypatch.setattr(settings, "pixabay_portrait_only", False)


def test_query_variants():
    assert query_variants("cat jumping fence") == ["cat jumping fence", "cat jumping"]
    assert query_variants("cat") == ["cat"]


def test_prefers_portrait_and_skips_used(tmp_path):
    client, _ = pixabay({"cat": [hit(1, 1920, 1080), hit(2, 1080, 1920), hit(3, 1080, 1920)]})
    px = PixabayAdapter(client, cache_dir=tmp_path / "cache")

    first = px.find_clip("cat", tmp_path / "a", 5)
    second = px.find_clip("cat", tmp_path / "b", 5)
    third = px.find_clip("cat", tmp_path / "c", 5)

    assert first.data["source_url"].endswith("/2/")
    assert second.data["source_url"].endswith("/3/")
    assert third.data["source_url"].endswith("/1/")
    assert first.data["author"] == "user2"
    assert (tmp_path / "a.mp4").read_bytes() == b"clip"


def test_portrait_only(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "pixabay_portrait_only", True)
    client, _ = pixabay({"cat": [hit(1, 1920, 1080)]})
    assert PixabayAdapter(client, cache_dir=tmp_path).find_clip("cat", tmp_path / "a", 5) is None


def test_shortens_query_and_caches(tmp_path):
    client, searches = pixabay({"octopus coral": [hit(5, 1080, 1920)]})
    px = PixabayAdapter(client, cache_dir=tmp_path / "cache")
    result = px.find_clip("octopus coral reef", tmp_path / "a", 5)
    assert searches == ["octopus coral reef", "octopus coral"]
    assert result.data["query"] == "octopus coral"

    PixabayAdapter(client, cache_dir=tmp_path / "cache").find_clip("octopus coral reef", tmp_path / "b", 5)
    assert searches == ["octopus coral reef", "octopus coral"]


def test_irrelevant_tags_rejected(tmp_path):
    client, _ = pixabay({"neutron star": [hit(1, 1920, 1080, tags="night, star, mountain, timelapse")]})
    assert PixabayAdapter(client, cache_dir=tmp_path).find_clip("neutron star", tmp_path / "a", 5) is None


def test_too_short_clips_ignored(tmp_path):
    client, _ = pixabay({"cat": [hit(1, 1080, 1920, duration=2)]})
    assert PixabayAdapter(client, cache_dir=tmp_path).find_clip("cat", tmp_path / "a", 6) is None


def fal(result):
    def handler(request: httpx.Request):
        url = str(request.url)
        if request.method == "POST":
            return httpx.Response(200, json={"status_url": "https://queue.fal.run/x/status",
                                             "response_url": "https://queue.fal.run/x"})
        if url.endswith("/status"):
            return httpx.Response(200, json={"status": "COMPLETED"})
        if url == "https://queue.fal.run/x":
            return httpx.Response(200, json=result)
        return httpx.Response(200, content=b"jpeg")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fal_image(tmp_path):
    client = fal({"images": [{"url": "https://fal.media/img.jpg"}], "has_nsfw_concepts": [False]})
    result = FalImages(client, poll_seconds=0).find_clip("cat", tmp_path / "v1", 5, "cats")
    assert result.data["kind"] == "image"
    assert result.data["path"].name == "v1.jpg"
    assert result.cost_eur == settings.fal_image_cost_eur


def test_fal_image_nsfw_rejected(tmp_path):
    client = fal({"images": [{"url": "x"}], "has_nsfw_concepts": [True]})
    with pytest.raises(ApiError):
        FalImages(client, poll_seconds=0).find_clip("cat", tmp_path / "v1", 5)


def test_media_chain(monkeypatch):
    monkeypatch.setattr(settings, "media_provider", "pixabay,fal_images")
    assert [p.name for p in factory.media_chain()] == ["Pixabay", "fal.ai attēli"]
    monkeypatch.setattr(settings, "pixabay_api_key", "")
    assert [p.name for p in factory.media_chain()] == ["fal.ai attēli"]


class FakeJudge:
    def __init__(self, scores):
        self.scores = list(scores)
        self.calls = []

    def score(self, images, topic, scene):
        self.calls.append((list(images), topic, scene))
        out = self.scores[:len(images)]
        self.scores = self.scores[len(images):]
        return ApiResult(out, "openai", "vision.judge", units=len(images), cost_eur=0.001)


def test_judge_picks_best_thumbnail(tmp_path):
    client, _ = pixabay({"cat": [hit(1, 1080, 1920), hit(2, 1080, 1920), hit(3, 1920, 1080)]})
    px = PixabayAdapter(client, cache_dir=tmp_path)
    px.judge = FakeJudge([4, 6, 9])
    result = px.find_clip("cat", tmp_path / "a", 5, "Why cats land on their feet")

    assert result.data["source_url"].endswith("/3/")
    assert result.data["score"] == 9
    assert px.judge.calls[0][1] == "Why cats land on their feet"
    assert [c.operation for c in px.take_costs()] == ["vision.judge"]


def test_judge_rejects_loosely_related(tmp_path):
    client, _ = pixabay({"jellyfish swimming": [hit(1, 1080, 1920, tags="jellyfish, swimming, ocean")]})
    px = PixabayAdapter(client, cache_dir=tmp_path)
    px.judge = FakeJudge([5])
    assert px.find_clip("jellyfish swimming", tmp_path / "a", 5, "jellyfish") is None


def test_fal_image_retried_when_off_topic(tmp_path):
    client = fal({"images": [{"url": "https://fal.media/img.jpg"}]})
    fi = FalImages(client, poll_seconds=0)
    fi.judge = FakeJudge([3, 8])
    result = fi.find_clip("jellyfish", tmp_path / "v1", 5, "jellyfish")

    assert result.data["score"] == 8
    assert result.units == 2
    assert result.cost_eur == settings.fal_image_cost_eur * 2
    assert not (tmp_path / "v1_2.jpg").exists()
    assert len(fi.take_costs()) == 2
