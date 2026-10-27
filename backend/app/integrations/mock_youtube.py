import random
import string
from pathlib import Path

from app.integrations.base import ApiResult, VideoPlatform, maybe_fail

UPLOAD_UNITS = 1


class MockYouTube(VideoPlatform):
    name = "YouTube (mock)"

    def upload(self, video_path: Path, title: str, description: str, tags: list[str], channel_ref: str) -> ApiResult:
        maybe_fail("youtube")
        video_id = "".join(random.choices(string.ascii_letters + string.digits + "-_", k=11))
        return ApiResult(video_id, "youtube", "videos.insert", units=UPLOAD_UNITS, simulated=True)

    def fetch_stats(self, video_ids: list[str]) -> ApiResult:
        stats = {}
        for vid in video_ids:
            views = random.randint(50, 5000)
            stats[vid] = {"views": views, "likes": int(views * random.uniform(0.02, 0.08)),
                          "comments": int(views * random.uniform(0.001, 0.01))}
        return ApiResult(stats, "youtube", "videos.list", units=1, simulated=True)
